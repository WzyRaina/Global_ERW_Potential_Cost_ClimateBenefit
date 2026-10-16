library(tidyverse)
library(patchwork)

trade <- FALSE
maxcb <- TRUE
start_year=2025;
# start_year=2030;
# start_year=2035;
# start_year=2040;
# start_year=2050;

##==================== 1. 读入数据 ====================

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    # 次区域级净效益（Python 输出）
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_netbenefit_by_region_subregion.csv")
    )
    
    # 区域级净效益（Python 输出）
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_netbenefit_by_region.csv")
    )
  } else{
    # 次区域级净效益（Python 输出）
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_netbenefit_by_region_subregion.csv")
    )
    
    # 区域级净效益（Python 输出）
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_netbenefit_by_region.csv")
    )
  }
} else {
  if (isTRUE(trade)){
    # 次区域级净效益（Python 输出）
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_netbenefit_by_region_subregion.csv")
    )
    
    # 区域级净效益（Python 输出）
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_netbenefit_by_region.csv")
    )
  } else{
    # 次区域级净效益（Python 输出）
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_netbenefit_by_region_subregion.csv")
    )
    
    # 区域级净效益（Python 输出）
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_netbenefit_by_region.csv")
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

# 次区域表：映射名字
df_sub <- df_sub_raw %>%
  mutate(
    Region_ID    = as.integer(Region_ID),
    Subregion_ID = as.integer(Subregion_ID),
    Region       = region_labels[as.character(Region_ID)],
    Subregion    = subregion_labels[as.character(Subregion_ID)],
    NetBenefit   = Weighted_NetBenefit_USD_per_tCO2
  ) %>%
  filter(!is.na(Region), !is.na(Subregion))

# 区域顺序
region_order <- c("Asia", "Europe", "Africa", "Americas", "Oceania", "Antarctica")
df_sub$Region <- factor(df_sub$Region, levels = region_order)

# 区域表：映射名字
df_reg <- df_reg_raw %>%
  mutate(
    Region_ID   = as.integer(Region_ID),
    Region      = region_labels[as.character(Region_ID)],
    NetBenefit  = Weighted_NetBenefit_USD_per_tCO2
  ) %>%
  filter(!is.na(Region))

df_reg$Region <- factor(df_reg$Region, levels = region_order)

# facet strip label：只显示区域名
region_strip_labs <- setNames(levels(df_sub$Region), levels(df_sub$Region))

# 用于“净效益允许为负”的 y 轴留白
pad_mult_sub <- 0.18
pad_mult_reg <- 0.22

##==================== 3. 大图：次区域加权净效益柱状图 ====================

# 计算上下留白，避免负值/正值都贴边
ymin_sub <- min(df_sub$NetBenefit, 0, na.rm = TRUE)
ymax_sub <- max(df_sub$NetBenefit, 0, na.rm = TRUE)
pad_sub  <- (ymax_sub - ymin_sub) * pad_mult_sub
if (!is.finite(pad_sub) || pad_sub == 0) pad_sub <- 1

p_nb_sub <- ggplot(
  df_sub,
  aes(x = Subregion, y = NetBenefit)
) +
  # coord_cartesian(ylim = c(-700, 100)) +  # 只有withtrade时启用，其余时候注释掉
  geom_hline(yintercept = 0, linewidth = 0.4) +
  geom_col(fill = "#c9e3ac", color = "black", width = 0.9) +
  # 在柱子顶部/底部加数值标签（正值在上，负值在下）
  geom_text(
    aes(
      label = sprintf("%.1f", NetBenefit),
      vjust = ifelse(NetBenefit >= 0, -0.3, 1.2)
    ),
    size = 5,
    color = "black"
  ) +
  facet_grid(
    ~ Region,
    scales = "free_x",
    space  = "free_x",
    labeller = labeller(Region = as_labeller(region_strip_labs))
  ) +
  scale_y_continuous(
    limits = c(ymin_sub - pad_sub, ymax_sub + pad_sub),
    expand = expansion(mult = c(0, 0))
  ) +
  labs(
    x = NULL,
    y = expression("Net benefit ($ tCO"[2]^"-1"*")")
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

##==================== 4. 小图：区域加权净效益柱状图 ====================

ymin_reg <- min(df_reg$NetBenefit, 0, na.rm = TRUE)
ymax_reg <- max(df_reg$NetBenefit, 0, na.rm = TRUE)
pad_reg  <- (ymax_reg - ymin_reg) * pad_mult_reg
if (!is.finite(pad_reg) || pad_reg == 0) pad_reg <- 1

p_nb_region <- ggplot(
  df_reg,
  aes(x = Region, y = NetBenefit)
) +
  geom_hline(yintercept = 0, linewidth = 0.4) +
  geom_col(fill = "#c9e3ac", color = "black", width = 0.7) +
  geom_text(
    aes(
      label = sprintf("%.1f", NetBenefit),
      vjust = ifelse(NetBenefit >= 0, -0.4, 1.2)
    ),
    size = 4,
    color = "black"
  ) +
  scale_y_continuous(
    limits = c(ymin_reg - pad_reg, ymax_reg + pad_reg),
    expand = expansion(mult = c(0, 0))
  ) +
  labs(
    x = NULL,
    y = expression("Net benefit ($ tCO"[2]^"-1"*")")
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

final_nb_plot <- p_nb_sub +
  inset_element(
    p_nb_region,
    left   = 0.53,   # 可按需要微调
    bottom = 0.05,
    right  = 0.93,
    top    = 0.60,
    align_to = "panel"
  )

print(final_nb_plot)

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_region_subregion_netbenefit.svg"),
      final_nb_plot,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_region_subregion_netbenefit.svg"),
      final_nb_plot,
      width = 12, height = 7
    )
  }
} else {
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_region_subregion_netbenefit.svg"),
      final_nb_plot,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_region_subregion_netbenefit.svg"),
      final_nb_plot,
      width = 12, height = 7
    )
  }
}
##==================== 6. 单独绘制并保存大区净效益柱状图 ====================

# 重新计算留白 (以大区数据为准)
ymin_reg_only <- min(df_reg$NetBenefit, 0, na.rm = TRUE)
ymax_reg_only <- max(df_reg$NetBenefit, 0, na.rm = TRUE)
pad_reg_only  <- (ymax_reg_only - ymin_reg_only) * 0.20 # 留白系数设为 0.2
if (!is.finite(pad_reg_only) || pad_reg_only == 0) pad_reg_only <- 1

p_nb_reg_standalone <- ggplot(df_reg, aes(x = Region, y = NetBenefit)) +
  geom_hline(yintercept = 0, linewidth = 0.4) +
  # 颜色保持 #c9e3ac
  geom_col(fill = "#c9e3ac", color = "black", width = 0.65) + 
  
  # 柱顶标注：字体加大加粗，区分正负位置
  geom_text(
    aes(
      label = sprintf("%.1f", NetBenefit),
      vjust = ifelse(NetBenefit >= 0, -0.5, 1.3) # 稍微加大 vjust，避免贴太紧
    ),
    size  = 6.5,       # 字号加大
    color = "black",
    # fontface = "bold"  # 加粗
  ) +
  
  # Y轴范围设定
  scale_y_continuous(
    limits = c(ymin_reg_only - pad_reg_only, ymax_reg_only + pad_reg_only),
    expand = expansion(mult = c(0, 0))
  ) +
  
  labs(
    x = NULL,
    y = expression("Net benefit ($ tCO"[2]^"-1"*")")
  ) +
  
  # 样式主题设置：对齐之前的图表风格 (大字号、粗体)
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
    # 不需要图例
    legend.position = "none",
    
    # 边距
    plot.margin = margin(t = 20, r = 20, b = 20, l = 20)
  )

# 保存设置
save_width_nb <- 12
save_height_nb <- 6

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    save_path_nb <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_Region_Only_netbenefit.svg")
  } else{
    save_path_nb <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_Region_Only_netbenefit.svg")
  }
} else {
  if (isTRUE(trade)){
    save_path_nb <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_Region_Only_netbenefit.svg")
  } else{
    save_path_nb <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_Region_Only_netbenefit.svg")
  }
}

ggsave(save_path_nb, p_nb_reg_standalone, width = save_width_nb, height = save_height_nb)

print(paste("Saved Region-only Net Benefit chart to:", save_path_nb))