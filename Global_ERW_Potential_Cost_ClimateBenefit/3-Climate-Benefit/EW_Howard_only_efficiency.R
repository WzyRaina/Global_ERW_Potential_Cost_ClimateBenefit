## FAIR_Howard model
rm(list=ls())
gc() 

# ================= 1. 配置区域 =================
setwd("E:/wzy/3-Climate-Benefit");

# 核心参数
start_year <- 2025   
n_cores <- 20        # 建议保持 10 核
simulation_no <- 50  

# 路径定义
base_output_dir <- "E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/only_efficiency/outputs"
fair_output_dir <- file.path(base_output_dir, start_year, "FAIR_Output")
howard_output_dir <- file.path(base_output_dir, start_year, "Howard_Output")

if (!dir.exists(howard_output_dir)) dir.create(howard_output_dir, recursive = TRUE)
log_file_path <- file.path(howard_output_dir, "progress_log.txt")

file_T_base <- file.path(fair_output_dir, "Base_Results/T_base_samples.csv")
dir_samples <- file.path(fair_output_dir, "Samples_50") 
file_metadata <- file.path(fair_output_dir, "EW_result_number.csv") 

# ================= 2. 环境初始化 =================
library(data.table)
library(parallel)
library(doParallel)
library(foreach)

if (start_year == 2025){ Time_periods=36; year_target = seq(2025,2200,5); }
if (start_year == 2030){ Time_periods=35; year_target = seq(2030,2200,5); }
if (start_year == 2035){ Time_periods=34; year_target = seq(2035,2200,5); }
if (start_year == 2040){ Time_periods=33; year_target = seq(2040,2200,5); }
if (start_year == 2050){ Time_periods=31; year_target = seq(2050,2200,5); }

Time_seq = 1:Time_periods
FAIR_row_target = year_target - 1765

cat(">>> [1/2] Loading Metadata (Fixing Header Issue)...\n")

# 1. 读取巨大的 Metadata (37万列)
# 注意：使用 fread 读取大文件
meta_raw <- fread(file_metadata, header = FALSE)

# 清洗第一列标签（如果存在）
if (meta_raw[1, 1] == "Rock" || meta_raw[1, 1] == "Grid_ID") { 
  cat("    Removing label column...\n")
  meta_raw <- meta_raw[, -1] 
}

# 转置：将 5行 x N列 转为 N行 x 5列
cat("    Transposing metadata (this may take a moment)...\n")
metadata <- as.data.table(t(meta_raw))
colnames(metadata) <- c("Rock", "Size", "pH", "T", "Eff")

n_grids_meta <- nrow(metadata) 
cat(paste("    Total Tasks detected from Metadata:", n_grids_meta, "\n"))
# ---------------------------------------

# 读取其他数据
T_base_all <- fread(file_T_base, header = TRUE) 
T_base_filtered <- T_base_all[FAIR_row_target + 1, ] 
sample_ids <- colnames(T_base_all) 

scenario_sample <- read.csv("Climate_Benefit/Sample/climate_scenario_sample.csv", header=T)
Howard_pop_data <- as.matrix(fread("Climate_Benefit/Socioeconomic/outputs/DICE_data/rffsps_global_pop.csv", header=TRUE))
Howard_gdp_data <- as.matrix(fread("Climate_Benefit/Socioeconomic/outputs/DICE_data/rffsps_global_gdp.csv", header=TRUE))
Howard_data_template <- read.csv("Climate_Benefit/Damage/Howard/Howard_ssp245.csv")

# ================= 3. 并行计算 =================
cat(paste(">>> [2/2] Starting Parallel Processing...\n"))

cl <- makeCluster(n_cores)
registerDoParallel(cl)

vars_to_export <- c(
  "Time_periods", "year_target", "Time_seq", "FAIR_row_target",
  "n_grids_meta", "sample_ids", "scenario_sample", 
  "Howard_pop_data", "Howard_gdp_data", "Howard_data_template",
  "dir_samples", "howard_output_dir", "metadata", "start_year",
  "T_base_filtered", "log_file_path"
)
clusterExport(cl, varlist = vars_to_export)

clusterEvalQ(cl, {
  library(data.table)
  setDTthreads(1)
  setwd("E:/wzy/3-Climate-Benefit") 
})

results <- foreach(s_idx = 1:length(sample_ids), 
                   .packages = c('data.table'),
                   .errorhandling = "pass") %dopar% {
                     
                     # 日志函数
                     write_log <- function(msg) {
                       try({ cat(paste0("[", Sys.time(), "] ", msg, "\n"), file = log_file_path, append = TRUE) }, silent = TRUE)
                     }
                     
                     tryCatch({
                       sid_name <- sample_ids[s_idx]
                       output_file <- file.path(howard_output_dir, paste0("SCC_Sample_", sid_name, ".csv"))
                       
                       # ========================================================
                       # 智能跳过逻辑
                       # ========================================================
                       process_needed <- TRUE
                       
                       if (file.exists(output_file)) {
                         # 快速检查行数（只读第一列）
                         # 注意：fread 读取会有 header，所以行数可能是 n_grids_meta
                         # 或者 n_grids_meta + 1 (如果有header)
                         # 稳妥起见，看量级。
                         
                         check_dt <- fread(output_file, select = 1L)
                         existing_rows <- nrow(check_dt)
                         
                         # 如果现有文件的行数 等于 (或非常接近) 元数据行数，说明是最新的，可以跳过
                         # 如果只有 15000 行，而元数据有 370000 行，说明是旧文件，必须重跑
                         if (existing_rows >= n_grids_meta) {
                           process_needed <- FALSE
                           return(paste0("Skip (Up-to-date): ", sid_name))
                         } else {
                           write_log(paste0("Update needed for ", sid_name, ": Found ", existing_rows, " rows, expected ", n_grids_meta))
                         }
                       }
                       
                       if (process_needed) {
                         write_log(paste("Start Processing:", sid_name))
                         
                         # 1. 准备 Base 数据
                         base_col_name <- NULL
                         if (sid_name %in% names(T_base_filtered)) base_col_name <- sid_name
                         else {
                           clean_sid <- gsub("Sample_", "", sid_name); clean_sid <- gsub("X", "", clean_sid)
                           if (paste0("X", sid_name) %in% names(T_base_filtered)) base_col_name <- paste0("X", sid_name)
                           else if (clean_sid %in% names(T_base_filtered)) base_col_name <- clean_sid
                         }
                         if (is.null(base_col_name)) stop(paste("Base col not found:", sid_name))
                         vec_base_target <- as.numeric(T_base_filtered[[base_col_name]])
                         
                         # 2. 准备 Extra 数据
                         clean_sid <- gsub("Sample_", "", sid_name); clean_sid <- gsub("X", "", clean_sid)
                         extra_file_path <- file.path(dir_samples, paste0("T_extra_Sample_", sid_name, ".csv"))
                         if (!file.exists(extra_file_path)) extra_file_path <- file.path(dir_samples, paste0("T_extra_Sample_", clean_sid, ".csv"))
                         
                         if (!file.exists(extra_file_path)) {
                           stop(paste("T_extra file missing:", extra_file_path))
                         }
                         
                         # 读取大文件 T_extra (37万行)
                         dt_extra_raw <- fread(extra_file_path, header = FALSE)
                         mat_extra_full <- as.matrix(dt_extra_raw)
                         
                         n_data_rows <- nrow(mat_extra_full)
                         n_run <- min(n_grids_meta, n_data_rows) # 取两者最小值，防止越界
                         
                         # 截取对应年份的温度
                         mat_extra_target <- mat_extra_full[1:n_run, FAIR_row_target + 1, drop = FALSE]
                         
                         # 3. 准备 Howard 参数
                         target_sample_row <- as.integer(clean_sid) + 1
                         target_sample_idx <- scenario_sample$x[target_sample_row]
                         
                         # 动态构建 Howard_data
                         Howard_data <- Howard_data_template
                         # 注意索引越界保护
                         pop_col_idx <- target_sample_idx + 1
                         if(pop_col_idx > ncol(Howard_pop_data)) pop_col_idx <- ncol(Howard_pop_data)
                         
                         Howard_data[2,-1] <- Howard_pop_data[, pop_col_idx]
                         Howard_data[3,-1] <- Howard_gdp_data[, pop_col_idx]
                         
                         # 4. 加载 Howard 模型函数
                         source("Climate_Benefit/Damage/Howard/Howard_damage.R", local = TRUE)
                         eta = 1.24; prtp = 0.002
                         
                         # 计算 Base 损害
                         Howard_temp <- vec_base_target
                         Playground_model()
                         Consumption_base_cached <- C; Global_damage_base_cached <- DAMAGES
                         
                         # 预计算折现因子
                         rr_fixed_1.5 <- 1/((1+0.015)^(year_target-year_target[1]))
                         rr_fixed_2.0 <- 1/((1+0.02)^(year_target-year_target[1]))
                         rr_fixed_3.0 <- 1/((1+0.03)^(year_target-year_target[1]))
                         rr_fixed_5.0 <- 1/((1+0.05)^(year_target-year_target[1]))
                         
                         if (!exists("l")) l <- Howard_data[2,-1]
                         rr_tv <- 1/((1+prtp)^(year_target-year_target[1])) * (((Consumption_base_cached/l)/(Consumption_base_cached[1]/l[1]))^(0-eta))
                         rr_tv_ces <- 1/((1+prtp)^(year_target-year_target[1])) * (((Consumption_base_cached/l))^(0-eta))
                         cpc_base_val <- Consumption_base_cached / l
                         ramsey_norm_factor <- 1 / mean(cpc_base_val[1]^(0-eta))
                         scale_factor <- 5 * 10000
                         
                         # 初始化结果矩阵
                         results_matrix <- matrix(NA, nrow = n_run, ncol = 6) 
                         
                         # 5. 循环计算 Extra 损害
                         # 这里 n_run 应该是 37万，计算量较大，但 C语言循环在 R 中略慢
                         # 如果太慢，可以考虑矩阵化（Howard模型通常难以矩阵化），这里维持原样
                         for (g in 1:n_run) {
                           Howard_temp <- mat_extra_target[g, ]
                           Playground_model() # 核心耗时步骤
                           
                           delta_damage <- Global_damage_base_cached - DAMAGES
                           
                           results_matrix[g, 1] <- sum(delta_damage * rr_fixed_1.5) * scale_factor
                           results_matrix[g, 2] <- sum(delta_damage * rr_fixed_2.0) * scale_factor
                           results_matrix[g, 3] <- sum(delta_damage * rr_fixed_3.0) * scale_factor
                           results_matrix[g, 4] <- sum(delta_damage * rr_fixed_5.0) * scale_factor
                           results_matrix[g, 5] <- sum(delta_damage * rr_tv) * scale_factor
                           results_matrix[g, 6] <- sum(delta_damage * rr_tv_ces) * scale_factor * ramsey_norm_factor
                         }
                         
                         # 6. 保存结果
                         colnames(results_matrix) <- c("Fixed_0.015", "Fixed_0.02", "Fixed_0.03", "Fixed_0.05", "TimeVarying", "TimeVarying_CES")
                         dt_res <- as.data.table(results_matrix)
                         
                         # 匹配 Metadata (确保行数一致)
                         meta_subset <- metadata[1:n_run, ]
                         final_output <- cbind(meta_subset, dt_res)
                         
                         fwrite(final_output, output_file)
                         
                         write_log(paste("Finished:", sid_name, "| Rows Processed:", n_run))
                         return(paste0("Done: ", sid_name))
                       }
                       
                     }, error = function(e) {
                       err_msg <- paste("CRITICAL ERROR in", sample_ids[s_idx], ":", e$message)
                       write_log(err_msg)
                       return(err_msg)
                     })
                   }

stopCluster(cl)
cat(">>> All Done. \n")