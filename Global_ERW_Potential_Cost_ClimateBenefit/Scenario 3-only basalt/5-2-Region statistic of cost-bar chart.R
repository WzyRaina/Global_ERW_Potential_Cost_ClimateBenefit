library(tidyverse)
library(patchwork)

trade <- FALSE
maxcb <- TRUE
# start_year=2025;
# start_year=2030;
# start_year=2035;
# start_year=2040;
start_year=2050;

##==================== 1. 读入数据 ====================

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    # 次区域级成本（Python 输出）
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_cost_by_region_subregion.csv")
    )
    
    # 区域级成本（Python 输出）
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_cost_by_region.csv")
    )
  } else{
    # 次区域级成本（Python 输出）
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_cost_by_region_subregion.csv")
    )
    
    # 区域级成本（Python 输出）
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_cost_by_region.csv")
    )
  }
} else {
  if (isTRUE(trade)){
    # 次区域级成本（Python 输出）
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_cost_by_region_subregion.csv")
    )
    
    # 区域级成本（Python 输出）
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_cost_by_region.csv")
    )
  } else{
    # 次区域级成本（Python 输出）
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_cost_by_region_subregion.csv")
    )
    
    # 区域级成本（Python 输出）
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_cost_by_region.csv")
    )
  }
}

##==================== 2. 区域 / 次区域名字、预处理 ====================

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

## 次区域表：映射名字
df_sub <- df_sub_raw %>%
  mutate(
    Region_ID    = as.integer(Region_ID),
    Subregion_ID = as.integer(Subregion_ID),
    Region       = region_labels[as.character(Region_ID)],
    Subregion    = subregion_labels[as.character(Subregion_ID)],
    Cost         = Weighted_Cost_USD_per_tCO2
  ) %>%
  filter(!is.na(Region), !is.na(Subregion))

## 区域顺序
region_order <- c("Asia", "Europe", "Africa", "Americas", "Oceania", "Antarctica")
df_sub$Region <- factor(df_sub$Region, levels = region_order)

## 区域表：映射名字
df_reg <- df_reg_raw %>%
  mutate(
    Region_ID = as.integer(Region_ID),
    Region    = region_labels[as.character(Region_ID)],
    Cost      = Weighted_Cost_USD_per_tCO2
  ) %>%
  filter(!is.na(Region))

df_reg$Region <- factor(df_reg$Region, levels = region_order)

## 用于 facet 的 strip label：只显示区域名（不再加总量）
region_strip_labs <- setNames(
  levels(df_sub$Region),
  levels(df_sub$Region)
)

##==================== 3. 大图：次区域加权成本柱状图 ====================

p_cost_sub <- ggplot(
  df_sub,
  aes(x = Subregion, y = Cost)
) +
  coord_cartesian(ylim = c(0, 1100)) +  # 只有withtrade时启用，其他时候注释掉
  geom_col(fill = "#00b4d8", color = "black", width = 0.9) +
  # 在每个柱子顶部加成本数字（$/tCO2）
  geom_text(
    aes(label = sprintf("%.1f", Cost)),
    vjust = -0.3,
    size = 5,
    color = "black"
  ) +
  facet_grid(
    ~ Region,
    scales = "free_x",
    space  = "free_x",
    labeller = labeller(Region = as_labeller(region_strip_labs))
  ) +
  labs(
    x   = NULL,
    y   = expression("Cost ($ tCO"[2]^"-1"*")")
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
    legend.position  = "none"
  )

##==================== 4. 小图：区域加权成本柱状图 ====================

p_cost_region <- ggplot(
  df_reg,
  aes(x = Region, y = Cost)
) +
  geom_col(fill = "#00b4d8", color = "black", width = 0.7) +
  geom_text(
    aes(label = sprintf("%.1f", Cost)),
    vjust = -0.4,
    size = 4,
    color = "black"
  ) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.18))) +
  labs(
    x = NULL,
    y = expression("Cost ($ tCO"[2]^"-1"*")")
  ) +
  theme_classic(base_size = 10) +
  theme(
    axis.text.x = element_text(angle = 0, hjust = 0.5, size = 14),
    axis.text.y = element_text(size = 14),
    axis.title  = element_text(size = 16),
    legend.position = "none",
    plot.margin = margin(2, 2, 2, 2)
  )

##==================== 5. 镶嵌小图到大图 ====================

p_cost_region_small <- p_cost_region

final_cost_plot <- p_cost_sub +
  inset_element(
    p_cost_region_small,
    left   = 0.53,   # 可以继续微调
    bottom = 0.40,
    right  = 0.93,
    top    = 0.95,
    align_to = "panel"
  )

print(final_cost_plot)

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_region_subregion_cost.svg"),
      final_cost_plot,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_region_subregion_cost.svg"),
      final_cost_plot,
      width = 12, height = 7
    )
  }
} else {
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_region_subregion_cost.svg"),
      final_cost_plot,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_region_subregion_cost.svg"),
      final_cost_plot,
      width = 12, height = 7
    )
  }
}
##==================== 6. 单独绘制并保存大区成本柱状图 ====================

p_cost_region_standalone <- ggplot(df_reg, aes(x = Region, y = Cost)) +
  # 颜色保持一致(#00b4d8)，width 0.65 保持视觉美观
  geom_col(fill = "#00b4d8", color = "black", width = 0.65) + 
  
  # 柱顶标注：字体加大加粗
  geom_text(
    aes(label = sprintf("%.1f", Cost)),
    vjust = -0.5,
    size  = 6.5,       # 字号加大
    color = "black",
    # fontface = "bold"  # 加粗
  ) +
  
  # 自动扩展Y轴，防止文字被切
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  
  labs(
    x = NULL,
    y = expression("Cost ($ tCO"[2]^"-1"*")")
  ) +
  
  # 样式主题设置：对齐之前的图表风格
  theme_classic(base_size = 18) +
  theme(
    # X轴文字
    axis.text.x = element_text(
      size = 22,        
      color = "black", 
      # face = "bold",    
      margin = margin(t = 8)
    ),
    # Y轴文字
    axis.text.y = element_text(
      size = 20,        
      color = "black"
    ),
    # Y轴标题
    axis.title.y = element_text(
      size = 24,        
      face = "bold", 
      margin = margin(r = 15)
    ),
    # 只有一个变量，不需要图例
    legend.position = "none",
    
    # 边距
    plot.margin = margin(t = 20, r = 20, b = 20, l = 20)
  )

# 保存参数
save_width_cost <- 12
save_height_cost <- 6

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    save_path_cost <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_Region_Only_cost.svg")
  } else{
    save_path_cost <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_Region_Only_cost.svg")
  }
} else {
  if (isTRUE(trade)){
    save_path_cost <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_Region_Only_cost.svg")
  } else{
    save_path_cost <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_Region_Only_cost.svg")
  }
}

ggsave(save_path_cost, p_cost_region_standalone, width = save_width_cost, height = save_height_cost)

print(paste("Saved Region-only Cost chart to:", save_path_cost))