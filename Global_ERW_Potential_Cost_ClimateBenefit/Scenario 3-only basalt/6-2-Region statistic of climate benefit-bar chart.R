library(tidyverse)

trade <- FALSE
maxcb <- TRUE
start_year=2025;
# start_year=2030;
# start_year=2035;
# start_year=2040;
# start_year=2050;

#==================== 1) 读入两个 csv ====================
if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_climatebenefit_by_region_subregion.csv")
    )
    
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_climatebenefit_by_region.csv")
    )
  } else{
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_climatebenefit_by_region_subregion.csv")
    )
    
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_climatebenefit_by_region.csv")
    )
  }
} else {
  if (isTRUE(trade)){
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_climatebenefit_by_region_subregion.csv")
    )
    
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_climatebenefit_by_region.csv")
    )
  } else{
    df_sub_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_climatebenefit_by_region_subregion.csv")
    )
    
    df_reg_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_climatebenefit_by_region.csv")
    )
  }
}

#==================== 2) 名称映射 ====================
region_labels <- c(
  `1`="Asia", `2`="Americas", `3`="Africa", `4`="Europe", `5`="Oceania", `6`="Antarctica"
)

subregion_labels <- c(
  `1`="South-\nEastern\nAsia", `2`="South\nAmerica", `3`="Western\nAsia", `4`="Southern\nAsia",
  `5`="Eastern\nAsia", `6`="Eastern\nAfrica", `7`="Western\nEurope", `8`="Northern\nAfrica",
  `9`="Central\nAmerica", `10`="Middle\nAfrica", `11`="Eastern\nEurope", `12`="Southern\nAfrica",
  `13`="Caribbean", `14`="Central\nAsia", `15`="Northern\nEurope", `16`="Southern\nEurope",
  `17`="Western\nAfrica", `18`="Northern\nAmerica", `19`="Melanesia", `20`="Antarctica",
  `21`="Australia\nand\nNew Zealand", `22`="Polynesia", `23`="Seven seas\n(open ocean)", `24`="Micronesia"
)

region_order <- c("Asia","Europe","Africa","Americas","Oceania","Antarctica")

#==================== 3) 整理次区域数据（df_sub） ====================
df_sub <- df_sub_raw %>%
  mutate(
    Region_ID    = as.integer(Region_ID),
    Subregion_ID = as.integer(Subregion_ID),
    Region       = region_labels[as.character(Region_ID)],
    Subregion    = subregion_labels[as.character(Subregion_ID)],
    CB           = Weighted_ClimateBenefit_USD_per_tCO2,   # 列名
    Type         = "Subregion"
  ) %>%
  filter(!is.na(Region), !is.na(Subregion)) %>%
  mutate(Region = factor(Region, levels = region_order))

#==================== 4) 整理区域 Total 数据（df_reg） ====================
df_reg <- df_reg_raw %>%
  mutate(
    Region_ID = as.integer(Region_ID),
    Region    = region_labels[as.character(Region_ID)],
    Subregion = "Total",
    CB        = Weighted_ClimateBenefit_USD_per_tCO2,      # 列名
    Type      = "Total"
  ) %>%
  filter(!is.na(Region)) %>%
  mutate(Region = factor(Region, levels = region_order))

#==================== 5) 合并 + 加空隙 + 生成“Region 内顺序编号” ====================
df_plot <- bind_rows(df_sub, df_reg) %>%
  mutate(Subregion = trimws(Subregion))

# 先给每个 Region 内次区域一个顺序号（按顺序：这里按 Subregion_ID 的数字顺序）
df_plot_ordered <- df_plot %>%
  group_by(Region) %>%
  mutate(
    ord = case_when(
      Type == "Subregion" ~ dense_rank(Subregion),  # 也可以改成按 Subregion_ID 排
      Type == "Total"     ~ 9998L                   # 先预留很大，确保靠后
    )
  ) %>%
  ungroup()

df_plot2 <- bind_rows(df_plot_ordered) %>%
  mutate(
    # 关键：用 Region + ord 生成唯一 x_id（这样 Total 必定最大 ord，必定最后）
    x_id = paste0(as.character(Region), "__", sprintf("%04d", ord), "__", Subregion)
  )

# 把 x_id 设为 factor，levels 按 Region 顺序 + ord 排序
x_levels <- df_plot2 %>%
  arrange(Region, ord) %>%
  distinct(x_id) %>%
  pull(x_id)

df_plot2 <- df_plot2 %>%
  mutate(x_id = factor(x_id, levels = x_levels))

# x 轴显示文字：取最后一段（Subregion/Total/空格）
x_lab <- function(x) sub("^.*__[^_]+__", "", x)

#==================== 6) 画图（Total 换颜色） ====================
p <- ggplot(df_plot2, aes(x = x_id, y = CB, fill = Type)) +
  geom_col(color = "black", width = 0.9, na.rm = TRUE) +
  geom_text(
    data = df_plot2,
    aes(label = sprintf("%.1f", CB)),
    vjust = -0.3,
    size = 5,
    color = "black",
    na.rm = TRUE
  ) +
  facet_grid(~ Region, scales = "free_x", space = "free_x") +
  scale_x_discrete(labels = x_lab, drop = TRUE) +
  scale_fill_manual(
    values = c(Subregion = "#6a994e", Total = "#bc4749"),
    breaks = c("Subregion","Total")
  ) +
  labs(
    x = NULL,
    y = expression("Climate benefit ($ tCO"[2]^"-1"*")"),
    fill = NULL
  ) +
  theme_classic(base_size = 14) +
  theme(
    strip.background = element_blank(),
    strip.text       = element_text(face = "bold", size = 16),
    panel.spacing.x  = unit(1.8, "lines"),
    axis.text.x      = element_text(
      angle = 0, hjust = 0.5, vjust = 1, size = 9.5, color = "black"
    ),
    axis.text.y      = element_text(size = 18),
    axis.title.y     = element_text(size = 22),
    legend.position  = c(0.95, 0.95),
    legend.title     = element_blank(),
    legend.text      = element_text(size = 15)
  ) +
  coord_cartesian(clip = "off") +
  scale_y_continuous(expand = expansion(mult = c(0, 0.20)))

print(p)

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_region_subregion_climatebenefit_totalcol.svg"),
      p,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_region_subregion_climatebenefit_totalcol.svg"),
      p,
      width = 12, height = 7
    )
  }
} else {
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_region_subregion_climatebenefit_totalcol.svg"),
      p,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_region_subregion_climatebenefit_totalcol.svg"),
      p,
      width = 12, height = 7
    )
  }
}
#==================== 7) 单独绘制并保存大区 Climate Benefit 柱状图 ====================

# 直接使用 df_reg，因为它已经包含了 Region 和 CB 数据
# Region 因子水平在前面已经设置好，所以顺序是对的 (Asia -> Antarctica)

p_reg_only <- ggplot(df_reg, aes(x = Region, y = CB)) +
  # 颜色使用与上面大图中 Total 相同的颜色 (#bc4749)
  geom_col(fill = "#6a994e", color = "black", width = 0.65) + 
  
  # 柱顶标注：字体加大加粗
  geom_text(
    aes(label = sprintf("%.1f", CB)),
    vjust = -0.5,
    size  = 6.5,       # 字号加大
    color = "black",
    # fontface = "bold"  # 加粗
  ) +
  
  # 扩展Y轴，防止文字溢出
  scale_y_continuous(expand = expansion(mult = c(0, 0.20))) +
  
  labs(
    x = NULL,
    y = expression("Climate benefit ($ tCO"[2]^"-1"*")")
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
save_width_cb <- 12
save_height_cb <- 6

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    save_path_cb <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_Region_Only_climatebenefit.svg")
  } else{
    save_path_cb <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_Region_Only_climatebenefit.svg")
  }
} else {
  if (isTRUE(trade)){
    save_path_cb <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_Region_Only_climatebenefit.svg")
  } else{
    save_path_cb <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_Region_Only_climatebenefit.svg")
  }
}

ggsave(save_path_cb, p_reg_only, width = save_width_cb, height = save_height_cb)

print(paste("Saved Region-only Climate Benefit chart to:", save_path_cb))