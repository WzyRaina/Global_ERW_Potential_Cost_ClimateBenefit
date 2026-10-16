# 代替arcgis绘制地图，增加有效潜力(黄色斜线)叠加层及封顶短线
# 包含统一图例生成（多年潜力版本）

library(tidyverse)
library(patchwork)
library(ggpattern) 

trade <- FALSE
maxcb <- TRUE
start_year=2025;
# start_year=2030;
# start_year=2035;
# start_year=2040;
# start_year=2050;

#==================== 1. 读入并预处理 ====================

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    df_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_potential_by_region_subregion (multi-year).csv")
    )
  } else{
    df_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_potential_by_region_subregion (multi-year).csv")
    )
  }
} else {
  if (isTRUE(trade)){
    df_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_potential_by_region_subregion (multi-year).csv")
    )
  } else{
    df_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_potential_by_region_subregion (multi-year).csv")
    )
  }
}

## 区域 / 次区域名字 -----------------
region_labels <- c(
  `1` = "Asia",
  `2` = "Americas",
  `3` = "Africa",
  `4` = "Europe",
  `5` = "Oceania",
  `6` = "Antarctica"
)

subregion_labels <- c(
  `1`  = "South-\nEastern\nAsia",
  `2`  = "South\nAmerica",
  `3`  = "Western\nAsia",
  `4`  = "Southern\nAsia",
  `5`  = "Eastern\nAsia",
  `6`  = "Eastern\nAfrica",
  `7`  = "Western\nEurope",
  `8`  = "Northern\nAfrica",
  `9`  = "Central\nAmerica",
  `10` = "Middle\nAfrica",
  `11` = "Eastern\nEurope",
  `12` = "Southern\nAfrica",
  `13` = "Caribbean",
  `14` = "Central\nAsia",
  `15` = "Northern\nEurope",
  `16` = "Southern\nEurope",
  `17` = "Western\nAfrica",
  `18` = "Northern\nAmerica",
  `19` = "Melanesia",
  `20` = "Antarctica",
  `21` = "Australia\nand\nNew Zealand",
  `22` = "Polynesia",
  `23` = "Seven seas\n(open ocean)",
  `24` = "Micronesia"
)

## 映射名字 + 过滤 NA ----------------------------------------
df <- df_raw %>%
  mutate(
    Region_ID    = as.integer(Region_ID),
    Subregion_ID = as.integer(Subregion_ID),
    Region       = region_labels[as.character(Region_ID)],
    Subregion    = subregion_labels[as.character(Subregion_ID)],
    Potential_Mt = Total_Potential_MtCO2_yr,
    Potential_Gt = Total_Potential_GtCO2_yr,
    Valid_Potential_Gt = Positive_NetBenefit_Potential_GtCO2_yr  # 新增有效潜力映射
  ) %>%
  filter(!is.na(Region), !is.na(Subregion))

# 区域顺序
region_order <- c("Asia", "Europe", "Africa", "Americas", "Oceania", "Antarctica")
df$Region <- factor(df$Region, levels = region_order)

#==================== 2. 每个大区 & 次区域总潜力 ====================

## 大区总潜力（小图 & 单独大图用）
region_pot <- df %>%
  group_by(Region) %>%
  summarise(
    Total_Gt = sum(Potential_Gt, na.rm = TRUE),
    Valid_Gt = sum(Valid_Potential_Gt, na.rm = TRUE),
    .groups = "drop"
  )

## strip label：这里只要 Region 名，不加总量
region_strip_labs <- setNames(
  levels(df$Region),
  levels(df$Region)
)

## 次区域总潜力（大图柱顶用）
subregion_pot <- df %>%
  group_by(Region, Subregion) %>%
  summarise(
    Total_Gt = sum(Potential_Gt, na.rm = TRUE),
    Valid_Gt = sum(Valid_Potential_Gt, na.rm = TRUE),
    .groups = "drop"
  )

pot_breaks <- c("Total Potential", "Cost-effective Potential")

#==================== 3. 大图：次区域潜力柱状图 ====================

p_sub_pot <- ggplot(df) +
  # 1. 绘制底层：总潜力 
  geom_col_pattern(
    aes(x = Subregion, y = Potential_Gt, fill = "Total Potential", pattern = "Total Potential", pattern_fill = "Total Potential"), 
    color = "black", width = 0.9
  ) +
  
  # 2. 绘制叠加层：有效潜力 
  geom_col_pattern(
    aes(x = Subregion, y = Valid_Potential_Gt, fill = "Cost-effective Potential", pattern = "Cost-effective Potential", pattern_fill = "Cost-effective Potential"),
    color = "black",          
    pattern_angle = 45,
    pattern_density = 0.3,    
    pattern_spacing = 0.025,
    pattern_color = NA,
    width = 0.9
  ) +
  
  # 3. 绘制超宽的封顶黄色短线
  geom_errorbar(
    data = subregion_pot %>% filter(Valid_Gt > 0),
    aes(x = Subregion, ymin = Valid_Gt, ymax = Valid_Gt),
    width = 0.98,            
    color = "#FFD700",       
    linewidth = 1.0          
  ) +
  
  # 4. 标注：总潜力
  geom_text(
    data = subregion_pot,
    aes(x = Subregion, y = Total_Gt, label = sprintf("%.2f", Total_Gt)),
    vjust = -0.3,
    size = 5,
    color = "black"
  ) +
  
  # 5. 标注：有效潜力
  geom_text(
    data = subregion_pot %>% filter(Valid_Gt > 0), 
    aes(x = Subregion, y = Valid_Gt, label = sprintf("%.2f", Valid_Gt)),
    vjust = -0.8,         
    size = 4.5,
    color = "#FFD700",    
    fontface = "bold"     
  ) +
  
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  facet_grid(
    ~ Region,
    scales = "free_x",
    space  = "free_x",
    labeller = labeller(Region = as_labeller(region_strip_labs))
  ) +
  
  # 使用 scale_xxx_manual 强行绑定图例样式
  scale_fill_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = "#168AAD", "Cost-effective Potential" = "transparent")) +
  scale_pattern_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = "none", "Cost-effective Potential" = "stripe")) +
  scale_pattern_fill_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = NA, "Cost-effective Potential" = "#FFD700")) +
  
  # 合并图例，避免重复出现色块
  guides(
    fill = guide_legend(ncol = 1, byrow = TRUE, override.aes = list(color = "black")), 
    pattern = guide_legend(ncol = 1, byrow = TRUE),
    pattern_fill = guide_legend(ncol = 1, byrow = TRUE)
  ) +
  
  labs(
    x   = NULL,
    y   = expression("Potential (GtCO"[2] * "/yr)")
  ) +
  theme_classic(base_size = 14) +
  theme(
    strip.background = element_blank(),
    strip.text       = element_text(face = "bold", size = 16),
    panel.spacing.x  = unit(1.4, "lines"),
    axis.text.x      = element_text(
      angle = 0, hjust = 0.5, vjust = 1, size = 9.5, color = "black"
    ),
    axis.text.y      = element_text(size = 18),
    axis.title.y     = element_text(size = 22),
    
    # 布置大图图例位置
    legend.position      = c(0.01, 0.99),      
    legend.justification = c(0, 1),            
    legend.background    = element_rect(fill = alpha("white", 0.9), color = NA), 
    legend.margin        = margin(8, 8, 8, 8),
    legend.text          = element_text(size = 14),         
    legend.key.size      = unit(0.7, "cm"),                 
    legend.spacing.y     = unit(0.2, "cm")
  )

#==================== 4. 小图：区域总潜力柱状图 ====================

p_region_pot <- ggplot(region_pot) +
  geom_col_pattern(
    aes(x = Region, y = Total_Gt, fill = "Total Potential", pattern = "Total Potential", pattern_fill = "Total Potential"), 
    color = "black", width = 0.7
  ) +
  
  # 叠加层：有效潜力
  geom_col_pattern(
    aes(x = Region, y = Valid_Gt, fill = "Cost-effective Potential", pattern = "Cost-effective Potential", pattern_fill = "Cost-effective Potential"),
    color = "black", 
    pattern_angle = 45, pattern_density = 0.3, pattern_spacing = 0.025, pattern_color = NA,
    width = 0.7
  ) +
  
  # 小图封顶短线
  geom_errorbar(
    data = region_pot %>% filter(Valid_Gt > 0),
    aes(x = Region, ymin = Valid_Gt, ymax = Valid_Gt),
    width = 0.82,            
    color = "#FFD700",
    linewidth = 1.0
  ) +
  
  # 总潜力标注
  geom_text(
    aes(x = Region, y = Total_Gt, label = sprintf("%.2f", Total_Gt)),
    vjust = -0.3, size = 4, color = "black"
  ) +
  
  # 小图有效潜力标注
  geom_text(
    data = region_pot %>% filter(Valid_Gt > 0),
    aes(x = Region, y = Valid_Gt, label = sprintf("%.2f", Valid_Gt)),
    vjust = -0.8,            
    size = 3.5, 
    color = "#FFD700", 
    fontface = "bold"
  ) +
  
  scale_y_continuous(expand = expansion(mult = c(0, 0.18))) +
  
  # 小图中保持 scale 一致，但强制不显示图例 (guide="none")
  scale_fill_manual(values = c("Total Potential" = "#168AAD", "Cost-effective Potential" = "transparent"), guide = "none") +
  scale_pattern_manual(values = c("Total Potential" = "none", "Cost-effective Potential" = "stripe"), guide = "none") +
  scale_pattern_fill_manual(values = c("Total Potential" = NA, "Cost-effective Potential" = "#FFD700"), guide = "none") +
  
  labs(
    x = NULL,
    y = expression("Potential (GtCO"[2] * "/yr)")
  ) +
  theme_classic(base_size = 10) +
  theme(
    axis.text.x = element_text(angle = 0, hjust = 0.5, size = 14),
    axis.text.y = element_text(size = 14),
    axis.title  = element_text(size = 16),
    legend.position = "none",
    plot.margin = margin(2, 2, 2, 2)
  )

#==================== 5. 镶嵌小图到大图 ====================

final_potential_plot <- p_sub_pot +
  inset_element(
    p_region_pot,
    left   = 0.33,
    bottom = 0.40,
    right  = 0.73,
    top    = 0.95,
    align_to = "panel"
  )

print(final_potential_plot)

# 保存组合图
if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_region_subregion_potential (multi-year).svg"),
      final_potential_plot,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_region_subregion_potential (multi-year).svg"),
      final_potential_plot,
      width = 12, height = 7
    )
  }
} else {
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_region_subregion_potential (multi-year).svg"),
      final_potential_plot,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_region_subregion_potential (multi-year).svg"),
      final_potential_plot,
      width = 12, height = 7
    )
  }
}

#==================== 6. 单独绘制并保存大区潜力柱状图 ====================

p_region_pot_standalone <- ggplot(region_pot) +
  geom_col_pattern(
    aes(x = Region, y = Total_Gt, fill = "Total Potential", pattern = "Total Potential", pattern_fill = "Total Potential"), 
    color = "black", width = 0.65
  ) + 
  
  geom_col_pattern(
    aes(x = Region, y = Valid_Gt, fill = "Cost-effective Potential", pattern = "Cost-effective Potential", pattern_fill = "Cost-effective Potential"),
    color = "black", 
    pattern_angle = 45, pattern_density = 0.3, pattern_spacing = 0.025, pattern_color = NA,
    width = 0.65
  ) +
  
  geom_errorbar(
    data = region_pot %>% filter(Valid_Gt > 0),
    aes(x = Region, ymin = Valid_Gt, ymax = Valid_Gt),
    width = 0.75,            
    color = "#FFD700",
    linewidth = 1.2
  ) +
  
  geom_text(
    aes(x = Region, y = Total_Gt, label = sprintf("%.2f", Total_Gt)),
    vjust = -0.5, size  = 6.5, color = "black"
  ) +
  
  geom_text(
    data = region_pot %>% filter(Valid_Gt > 0),
    aes(x = Region, y = Valid_Gt, label = sprintf("%.2f", Valid_Gt)),
    vjust = -0.8,            
    size = 6, 
    color = "#FFD700", 
    fontface = "bold"
  ) +
  
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  
  scale_fill_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = "#168AAD", "Cost-effective Potential" = "transparent")) +
  scale_pattern_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = "none", "Cost-effective Potential" = "stripe")) +
  scale_pattern_fill_manual(name = NULL, breaks = pot_breaks, values = c("Total Potential" = NA, "Cost-effective Potential" = "#FFD700")) +
  
  guides(
    fill = guide_legend(ncol = 1, byrow = TRUE, override.aes = list(color = "black")), 
    pattern = guide_legend(ncol = 1, byrow = TRUE),
    pattern_fill = guide_legend(ncol = 1, byrow = TRUE)
  ) +
  
  labs(
    x = NULL,
    y = expression("Potential (GtCO"[2] * "/yr)")
  ) +
  
  theme_classic(base_size = 18) +
  theme(
    axis.text.x = element_text(size = 22, color = "black", margin = margin(t = 8)),
    axis.text.y = element_text(size = 20, color = "black"),
    axis.title.y = element_text(size = 24, face = "bold", margin = margin(r = 15)),
    
    legend.position      = c(0.99, 0.99),      
    legend.justification = c(1, 1),            
    legend.background    = element_rect(fill = alpha("white", 0.9), color = NA), 
    legend.margin        = margin(8, 8, 8, 8),
    legend.text          = element_text(size = 22),         
    legend.key.size      = unit(1.0, "cm"),                 
    legend.spacing.y     = unit(0.4, "cm"),
    
    plot.margin = margin(t = 20, r = 20, b = 20, l = 20)
  )

# 保存参数
save_width_pot <- 12
save_height_pot <- 6

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    save_path_pot <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_Region_Only_potential (multi-year).svg")
  } else{
    save_path_pot <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_Region_Only_potential (multi-year).svg")
  }
} else {
  if (isTRUE(trade)){
    save_path_pot <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_Region_Only_potential (multi-year).svg")
  } else{
    save_path_pot <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_Region_Only_potential (multi-year).svg")
  }
}

ggsave(save_path_pot, p_region_pot_standalone, width = save_width_pot, height = save_height_pot)

print(paste("Saved Region-only Potential chart to:", save_path_pot))