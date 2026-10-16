# 绘制主要国家 Top 6 潜力对比：总潜力 vs 经济有效潜力 (嵌套柱状图)

library(tidyverse)
library(patchwork)
library(ggpattern) 

trade <- FALSE
maxcb <- TRUE
start_year = 2025
# start_year = 2030;
# start_year = 2035;
# start_year = 2040;
# start_year = 2050;

#==================== 1. 动态路径与数据读取 ====================

if (isTRUE(maxcb)){
  scenario_folder <- ifelse(isTRUE(trade), "maxclimatebenefit_withtrade", "maxclimatebenefit_notrade")
} else {
  scenario_folder <- ifelse(isTRUE(trade), "mincost_withtrade", "mincost_notrade")
}

base_path <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/", scenario_folder, "/")

# 自动处理带 (with trade) 后缀的文件名
suffix <- ifelse(isTRUE(trade), " (with trade).csv", ".csv")
pot_file <- paste0(base_path, "Country Potential Rank", suffix)
val_file <- paste0(base_path, "Country Cost-effective Potential Rank", suffix)

# 读取数据
df_pot <- read_csv(pot_file)
df_val <- read_csv(val_file)

#==================== 2. 数据合并、排序与 Top 6 筛选 ====================

# 将 Country Code 数字映射为真实的国家名字
country_name_mapping <- c(
  `231` = "USA",
  `247` = "India", 
  `246` = "China",
  `29` = "Brazil",
  `180` = "Russia",
  `12` = "Australia",
  `9` = "Argentina",
  `38` = "Canada",
  `67` = "Ethiopia",
  `205` = "Sudan",
  `159` = "Nigeria",
  `214` = "Thailnd",
  `140` = "Mexico",
  `195` = "South Africa",
  `114` = "Kazakhstan"
)

df_top10 <- df_pot %>%
  # 按照 Country Code 合并有效潜力数据
  left_join(df_val, by = "Country Code") %>%
  # 重命名列以便后续绘图
  rename(Total_Gt = Potential, Valid_Gt = `Cost-effective Potential`) %>%
  # 处理某些国家可能没有有效潜力导致 NA 的情况
  replace_na(list(Valid_Gt = 0)) %>%
  # 按总潜力降序排列
  arrange(desc(Total_Gt)) %>%
  # 截取前 6 名
  slice_head(n = 6) %>%
  # 映射国家名称
  mutate(
    Country_Name = case_when(
      as.character(`Country Code`) %in% names(country_name_mapping) ~ country_name_mapping[as.character(`Country Code`)],
      TRUE ~ paste0("Country_", `Country Code`) # 如果字典里没写，备用显示
    )
  )

# 将国家名称转换为因子，并按照 Total_Gt 的降序锁定顺序，防止 ggplot 自动按字母排序
df_top10$Country_Name <- factor(df_top10$Country_Name, levels = df_top10$Country_Name)

#==================== 3. 绘图配置与图例定义 ====================

pot_breaks <- c("Total Potential", "Cost-effective Potential")

p_country_top10 <- ggplot(df_top10, aes(x = Country_Name)) +
  
  # 1. 绘制底层：总潜力
  geom_col_pattern(
    aes(y = Total_Gt, fill = "Total Potential", pattern = "Total Potential", pattern_fill = "Total Potential"), 
    color = "black", width = 0.75
  ) +
  
  # 2. 绘制外敷层：经济有效潜力 (透明填充，黄色斜线)
  geom_col_pattern(
    aes(y = Valid_Gt, fill = "Cost-effective Potential", pattern = "Cost-effective Potential", pattern_fill = "Cost-effective Potential"),
    color = "black",          
    pattern_angle = 45,
    pattern_density = 0.3,    
    pattern_spacing = 0.025,
    pattern_color = NA,
    width = 0.75
  ) +
  
  # 3. 绘制超宽的封顶黄色短线
  geom_errorbar(
    aes(ymin = Valid_Gt, ymax = Valid_Gt),
    width = 0.98,            
    color = "#FFD700",       
    linewidth = 1.0          
  ) +
  
  # 4. 标注：总潜力 (黑色，在柱子外侧)
  geom_text(
    aes(y = Total_Gt, label = sprintf("%.2f", Total_Gt)),
    vjust = -0.4,
    size = 6.5,
    color = "black"
  ) +
  
  # 5. 标注：经济有效潜力 (黄色，放置到封顶短线的上方)
  geom_text(
    aes(y = Valid_Gt, label = sprintf("%.2f", Valid_Gt)),
    vjust = -0.8,         
    size = 6,
    color = "#FFD700",    
    fontface = "bold"     
  ) +
  
  # 适当放宽 Y 轴顶部空间，防止数字被切除
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  
  # 图例映射系统
  scale_fill_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = "#168AAD", "Cost-effective Potential" = "transparent")) +
  scale_pattern_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = "none", "Cost-effective Potential" = "stripe")) +
  scale_pattern_fill_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = NA, "Cost-effective Potential" = "#FFD700")) +
  
  guides(
    fill = guide_legend(ncol = 1, byrow = TRUE, override.aes = list(color = "black")), 
    pattern = guide_legend(
      ncol = 1, byrow = TRUE,
      override.aes = list(color = "black", pattern_density = 0.3, pattern_spacing = 0.025, pattern_color = NA)
    ),
    pattern_fill = guide_legend(
      ncol = 1, byrow = TRUE,
      override.aes = list(color = "black", pattern_density = 0.3, pattern_spacing = 0.025, pattern_color = NA)
    )
  ) +
  
  labs(
    x   = NULL,
    y   = expression("Potential (GtCO"[2] * ")")
  ) +
  
  theme_classic(base_size = 18) +
  theme(
    # X轴国家名称可能会比较长，若有重叠可适度调整 angle
    axis.text.x      = element_text(angle = 0, hjust = 0.5, vjust = 1, size = 22, color = "black"),
    axis.text.y      = element_text(size = 18, color = "black"),
    axis.title.y     = element_text(size = 24, face = "bold", margin = margin(r = 15)),
    
    # 图例配置：放在图表右上角
    legend.position      = c(0.98, 0.98),      
    legend.justification = c(1, 1),            
    legend.background    = element_rect(fill = alpha("white", 0.9), color = NA), 
    legend.margin        = margin(10, 10, 10, 10),
    legend.text          = element_text(size = 22),         
    legend.key.size      = unit(0.9, "cm"),                 
    legend.spacing.y     = unit(0.3, "cm"),
    
    plot.margin = margin(t = 20, r = 20, b = 20, l = 20)
  )

#==================== 4. 渲染与保存 ====================

print(p_country_top10)

out_folder_map <- paste0(base_path, "Map/")
dir.create(out_folder_map, recursive = TRUE, showWarnings = FALSE)

save_path <- paste0(out_folder_map, "Global_ERW_Top10_Country_Potential.svg")

# 宽度设置为 14 以容纳柱子
ggsave(save_path, p_country_top10, width = 12, height = 6)

print(paste("✅ 已成功保存 Top 6 国家潜力对比图至:", save_path))