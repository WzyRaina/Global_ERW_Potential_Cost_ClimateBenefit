library(tidyverse)
library(patchwork)
library(ggpattern)  # 必须加载此包以支持斜线阴影填充

trade <- FALSE
maxcb <- TRUE
start_year = 2025
# start_year = 2030
# start_year = 2035
# start_year = 2040
# start_year = 2050

##==================== 1. 动态路径与数据读取 ====================

# 依据开关生成对应的路径文件夹名
if (isTRUE(maxcb)) {
  scenario_folder <- ifelse(isTRUE(trade), "maxclimatebenefit_withtrade", "maxclimatebenefit_notrade")
} else {
  scenario_folder <- ifelse(isTRUE(trade), "mincost_withtrade", "mincost_notrade")
}

base_path <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/", scenario_folder, "/")

# 读取次区域数据
df_sub_cost <- read_csv(paste0(base_path, "EW_cost_by_region_subregion.csv")) %>%
  rename(Cost = Weighted_Cost_USD_per_tCO2)
df_sub_cb <- read_csv(paste0(base_path, "EW_climatebenefit_by_region_subregion.csv")) %>%
  rename(ClimateBenefit = Weighted_ClimateBenefit_USD_per_tCO2)
df_sub_nb <- read_csv(paste0(base_path, "EW_netbenefit_by_region_subregion.csv")) %>%
  rename(NetBenefit = Weighted_NetBenefit_USD_per_tCO2)

# 读取大区数据
df_reg_cost <- read_csv(paste0(base_path, "EW_cost_by_region.csv")) %>%
  rename(Cost = Weighted_Cost_USD_per_tCO2)
df_reg_cb <- read_csv(paste0(base_path, "EW_climatebenefit_by_region.csv")) %>%
  rename(ClimateBenefit = Weighted_ClimateBenefit_USD_per_tCO2)
df_reg_nb <- read_csv(paste0(base_path, "EW_netbenefit_by_region.csv")) %>%
  rename(NetBenefit = Weighted_NetBenefit_USD_per_tCO2)

##==================== 2. 数据合并与预处理 (保持宽数据结构) ====================

region_labels <- c(`1`="Asia", `2`="Americas", `3`="Africa", `4`="Europe", `5`="Oceania", `6`="Antarctica")
region_order <- c("Asia", "Europe", "Africa", "Americas", "Oceania", "Antarctica")

subregion_labels <- c(
  `1`="South-\nEastern\nAsia", `2`="South\nAmerica", `3`="Western\nAsia", `4`="Southern\nAsia",
  `5`="Eastern\nAsia", `6`="Eastern\nAfrica", `7`="Western\nEurope", `8`="Northern\nAfrica",
  `9`="Central\nAmerica", `10`="Middle\nAfrica", `11`="Eastern\nEurope", `12`="Southern\nAfrica",
  `13`="Caribbean", `14`="Central\nAsia", `15`="Northern\nEurope", `16`="Southern\nEurope",
  `17`="Western\nAfrica", `18`="Northern\nAmerica", `19`="Melanesia", `20`="Antarctica",
  `21`="Australia\nand\nNew Zealand", `22`="Polynesia", `23`="Seven seas\n(open ocean)", `24`="Micronesia"
)

# 合并次区域数据
df_sub <- df_sub_cost %>%
  left_join(df_sub_cb, by = c("Region_ID", "Subregion_ID")) %>%
  left_join(df_sub_nb, by = c("Region_ID", "Subregion_ID")) %>%
  mutate(
    Region = factor(region_labels[as.character(Region_ID)], levels = region_order),
    Subregion = subregion_labels[as.character(Subregion_ID)]
  ) %>%
  filter(!is.na(Region), !is.na(Subregion))

# 合并区域数据
df_reg <- df_reg_cost %>%
  left_join(df_reg_cb, by = "Region_ID") %>%
  left_join(df_reg_nb, by = "Region_ID") %>%
  mutate(
    Region = factor(region_labels[as.character(Region_ID)], levels = region_order)
  ) %>%
  filter(!is.na(Region))

# 用于 facet 的 strip label
region_strip_labs <- setNames(levels(df_sub$Region), levels(df_sub$Region))

# === 定义全局共用的图例排列顺序 ===
my_breaks <- c("Climate Benefit", "Cost", "Net Benefit")

##==================== 3. 绘制大图：次区域双向柱状图 ====================

ymin_sub <- -max(df_sub$Cost, na.rm = TRUE)
ymax_sub <- max(df_sub$ClimateBenefit, na.rm = TRUE)
pad_sub_y <- (ymax_sub - ymin_sub) * 0.15

p_sub <- ggplot(df_sub, aes(x = Subregion)) +
  geom_col_pattern(aes(y = -Cost, fill = "Cost", pattern = "Cost", pattern_fill = "Cost"), width = 0.75, color = "black") +
  geom_col_pattern(aes(y = ClimateBenefit, fill = "Climate Benefit", pattern = "Climate Benefit", pattern_fill = "Climate Benefit"), width = 0.75, color = "black") +
  geom_col_pattern(aes(y = NetBenefit, fill = "Net Benefit", pattern = "Net Benefit", pattern_fill = "Net Benefit"), 
                   pattern_angle = 45, pattern_density = 0.3, pattern_spacing = 0.025, pattern_color = NA, color = NA, width = 0.75) +
  
  geom_hline(yintercept = 0, color = "black", linewidth = 0.8) +
  geom_errorbar(aes(ymin = NetBenefit, ymax = NetBenefit), color = "#2a9d8f", width = 0.85, linewidth = 1.2) +
  
  geom_text(aes(y = ClimateBenefit, label = sprintf("%.1f", ClimateBenefit)), vjust = -0.6, size = 4.5) +
  geom_text(aes(y = -Cost, label = sprintf("%.1f", Cost)), vjust = 1.8, size = 4.5) +
  geom_text(data = filter(df_sub, NetBenefit >= 0), 
            aes(y = NetBenefit, label = sprintf("%.1f", NetBenefit)), vjust = -0.6, color = "#2a9d8f", fontface = "bold", size = 4.5) +
  geom_text(data = filter(df_sub, NetBenefit < 0), 
            aes(y = NetBenefit, label = sprintf("%.1f", NetBenefit)), vjust = 1.5, color = "#2a9d8f", fontface = "bold", size = 4.5) +
  
  facet_grid(~ Region, scales = "free_x", space = "free_x", labeller = labeller(Region = as_labeller(region_strip_labs))) +
  scale_y_continuous(labels = abs, limits = c(ymin_sub - pad_sub_y * 1, ymax_sub + pad_sub_y), expand = expansion(mult = c(0, 0))) +
  
  scale_fill_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = "#264653", "Cost" = "#e9c46a", "Net Benefit" = "transparent")) +
  scale_pattern_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = "none", "Cost" = "none", "Net Benefit" = "stripe")) +
  scale_pattern_fill_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = NA, "Cost" = NA, "Net Benefit" = "#2a9d8f")) +
  
  # === 修改：加上 byrow = TRUE 使垂直间距生效 ===
  guides(
    fill = guide_legend(ncol = 1, byrow = TRUE, override.aes = list(color = "black")), 
    pattern = guide_legend(ncol = 1, byrow = TRUE),
    pattern_fill = guide_legend(ncol = 1, byrow = TRUE)
  ) +
  
  labs(x = NULL, y = expression("Cost and Benefit ($ tCO"[2]^"-1"*")")) +
  theme_classic(base_size = 14) +
  theme(
    strip.background = element_blank(),
    strip.text       = element_text(face = "bold", size = 18),
    panel.spacing.x  = unit(1.4, "lines"),
    axis.text.x      = element_text(angle = 0, hjust = 0.5, vjust = 1, size = 10, color = "black"),
    axis.text.y      = element_text(size = 18),
    axis.title.y     = element_text(size = 22),
    
    legend.position      = c(0.01, 0.01),      
    legend.justification = c(0, 0),            
    legend.background    = element_rect(fill = alpha("white", 0.9), color = NA), 
    legend.margin        = margin(8, 8, 8, 8),
    
    # === 修改：放大字体、增加色块大小、增加垂直间距 ===
    legend.text          = element_text(size = 18),         # 字体变大
    legend.key.size      = unit(0.8, "cm"),                 # 图例色块变大，与大字体协调
    legend.spacing.y     = unit(0.3, "cm")                  # 选项之间的垂直距离
  )

##==================== 4. 绘制小图：大区双向柱状图 ====================

ymin_reg <- -max(df_reg$Cost, na.rm = TRUE)
ymax_reg <- max(df_reg$ClimateBenefit, na.rm = TRUE)
pad_reg_y <- (ymax_reg - ymin_reg) * 0.18

p_region <- ggplot(df_reg, aes(x = Region)) +
  geom_col_pattern(aes(y = -Cost, fill = "Cost", pattern = "Cost", pattern_fill = "Cost"), width = 0.75, color = "black") +
  geom_col_pattern(aes(y = ClimateBenefit, fill = "Climate Benefit", pattern = "Climate Benefit", pattern_fill = "Climate Benefit"), width = 0.75, color = "black") +
  geom_col_pattern(aes(y = NetBenefit, fill = "Net Benefit", pattern = "Net Benefit", pattern_fill = "Net Benefit"), 
                   pattern_angle = 45, pattern_density = 0.3, pattern_spacing = 0.025, pattern_color = NA, color = NA, width = 0.75) +
  
  geom_hline(yintercept = 0, color = "black", linewidth = 0.8) +
  geom_errorbar(aes(ymin = NetBenefit, ymax = NetBenefit), color = "#2a9d8f", width = 0.85, linewidth = 1.2) +
  
  geom_text(aes(y = ClimateBenefit, label = sprintf("%.1f", ClimateBenefit)), vjust = -0.3, size = 5) +
  geom_text(aes(y = -Cost, label = sprintf("%.1f", Cost)), vjust = 1.5, size = 5) +
  geom_text(data = filter(df_reg, NetBenefit >= 0), 
            aes(y = NetBenefit, label = sprintf("%.1f", NetBenefit)), vjust = -0.6, color = "#2a9d8f", fontface = "bold", size = 5) +
  geom_text(data = filter(df_reg, NetBenefit < 0), 
            aes(y = NetBenefit, label = sprintf("%.1f", NetBenefit)), vjust = 1.5, color = "#2a9d8f", fontface = "bold", size = 5) +
  
  scale_y_continuous(labels = abs, limits = c(ymin_reg - pad_reg_y, ymax_reg + pad_reg_y), expand = expansion(mult = c(0, 0))) +
  
  scale_fill_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = "#264653", "Cost" = "#e9c46a", "Net Benefit" = "transparent")) +
  scale_pattern_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = "none", "Cost" = "none", "Net Benefit" = "stripe")) +
  scale_pattern_fill_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = NA, "Cost" = NA, "Net Benefit" = "#2a9d8f")) +
  
  labs(x = NULL, y = expression("Cost and Benefit ($ tCO"[2]^"-1"*")")) +
  theme_classic(base_size = 12) +
  theme(
    axis.text.x = element_text(angle = 0, hjust = 0.5, size = 14),
    axis.text.y = element_text(size = 14),
    axis.title  = element_text(size = 16),
    legend.position = "none", # 镶嵌图中不显示图例
    plot.margin = margin(5, 5, 5, 5),
    panel.background = element_rect(fill = "white", color = "black")
  )

##==================== 5. 镶嵌小图到大图并保存 ====================

final_plot <- p_sub +
  inset_element(
    p_region,
    left   = 0.55, 
    bottom = 0.03,
    right  = 0.98,
    top    = 0.55, 
    align_to = "panel"
  )

out_folder_map <- paste0(base_path, "Map/")
dir.create(out_folder_map, recursive = TRUE, showWarnings = FALSE)

save_path_combined <- paste0(out_folder_map, "Global_ERW_combined_bidirectional_subregion.svg")
ggsave(save_path_combined, final_plot, width = 14, height = 8)
print(paste("Saved Combined Subregion + Region chart to:", save_path_combined))


##==================== 6. 单独绘制并保存大区双向柱状图 ====================

p_reg_standalone <- ggplot(df_reg, aes(x = Region)) +
  geom_col_pattern(aes(y = -Cost, fill = "Cost", pattern = "Cost", pattern_fill = "Cost"), width = 0.65, color = "black") +
  geom_col_pattern(aes(y = ClimateBenefit, fill = "Climate Benefit", pattern = "Climate Benefit", pattern_fill = "Climate Benefit"), width = 0.65, color = "black") +
  geom_col_pattern(aes(y = NetBenefit, fill = "Net Benefit", pattern = "Net Benefit", pattern_fill = "Net Benefit"), 
                   pattern_angle = 45, pattern_density = 0.3, pattern_spacing = 0.025, pattern_color = NA, color = NA, width = 0.65) +
  
  geom_hline(yintercept = 0, color = "black", linewidth = 0.8) +
  geom_errorbar(aes(ymin = NetBenefit, ymax = NetBenefit), color = "#2a9d8f", width = 0.75, linewidth = 1.2) +
  
  geom_text(aes(y = ClimateBenefit, label = sprintf("%.1f", ClimateBenefit)), vjust = -0.6, size = 6) +
  geom_text(aes(y = -Cost, label = sprintf("%.1f", Cost)), vjust = 1.8, size = 6) +
  geom_text(data = filter(df_reg, NetBenefit >= 0), 
            aes(y = NetBenefit, label = sprintf("%.1f", NetBenefit)), vjust = -0.6, color = "#2a9d8f", fontface = "bold", size = 6) +
  geom_text(data = filter(df_reg, NetBenefit < 0), 
            aes(y = NetBenefit, label = sprintf("%.1f", NetBenefit)), vjust = 1.5, color = "#2a9d8f", fontface = "bold", size = 6) +
  
  scale_y_continuous(labels = abs, limits = c(ymin_reg - pad_reg_y, ymax_reg + pad_reg_y), expand = expansion(mult = c(0, 0))) +
  
  scale_fill_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = "#264653", "Cost" = "#e9c46a", "Net Benefit" = "transparent")) +
  scale_pattern_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = "none", "Cost" = "none", "Net Benefit" = "stripe")) +
  scale_pattern_fill_manual(name = NULL, breaks = my_breaks, values = c("Climate Benefit" = NA, "Cost" = NA, "Net Benefit" = "#2a9d8f")) +
  
  # === 修改：加上 byrow = TRUE 使垂直间距生效 ===
  guides(
    fill = guide_legend(ncol = 1, byrow = TRUE, override.aes = list(color = "black")), 
    pattern = guide_legend(ncol = 1, byrow = TRUE),
    pattern_fill = guide_legend(ncol = 1, byrow = TRUE)
  ) +
  
  labs(x = NULL, y = expression("Cost and Benefit ($ tCO"[2]^"-1"*")")) +
  theme_classic(base_size = 18) +
  theme(
    axis.text.x = element_text(size = 22, color = "black", margin = margin(t = 8)),
    axis.text.y = element_text(size = 20, color = "black"),
    axis.title.y = element_text(size = 24, face = "bold", margin = margin(r = 15)),
    
    legend.position      = c(0.99, 0.01),      
    legend.justification = c(1, 0),            
    legend.background    = element_rect(fill = alpha("white", 0.9), color = NA), 
    legend.margin        = margin(8, 8, 8, 8),
    
    # === 修改：放大单独大图的字体、图例色块、增加垂直间距 ===
    legend.text          = element_text(size = 22),         # 字体变大
    legend.key.size      = unit(1.0, "cm"),                 # 图例色块变大
    legend.spacing.y     = unit(0.4, "cm"),                 # 选项之间的垂直距离
    
    plot.margin = margin(t = 20, r = 20, b = 20, l = 20)
  )

save_path_reg_only <- paste0(out_folder_map, "Global_ERW_combined_bidirectional_region_only.svg")
ggsave(save_path_reg_only, p_reg_standalone, width = 12, height = 7)
print(paste("Saved Region-only bidirectional chart to:", save_path_reg_only))