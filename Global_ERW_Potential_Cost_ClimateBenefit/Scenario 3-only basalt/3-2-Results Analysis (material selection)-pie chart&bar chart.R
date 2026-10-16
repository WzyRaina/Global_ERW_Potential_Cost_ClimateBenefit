# ====== pie chart ====== #

library(ggplot2)
library(ggrepel)
library(dplyr)
library(readr)
library(tidyverse)
library(patchwork)

trade <- FALSE
maxcb <- TRUE
start_year=2025;
# start_year=2030;
# start_year=2035;
# start_year=2040;
# start_year=2050;

# ==============================================================================
# PART 1: Pie Chart (保持不变)
# ==============================================================================

# 读取数据
if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    df <- read.csv(paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_summary_by_technology_area.csv"))
  } else{
    df <- read.csv(paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_summary_by_technology_area.csv"))
  }
} else {
  if (isTRUE(trade)){
    df <- read.csv(paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_summary_by_technology_area.csv"))
  } else{
    df <- read.csv(paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_summary_by_technology_area.csv"))
  }
}

# 筛选出 Scenario == "Scenario 3" 的数据
df <- df %>%
  filter(Scenario == "Scenario 3")

# 技术编号映射为组合名称
tech_labels <- c(
  "1" = "Basalt, 2μm",
  "2" = "Basalt, 10μm",
  "3" = "Basalt, 20μm",
  "4" = "Basalt, 50μm"
)

# 构造带百分比的图例标签
df <- df %>%
  mutate(
    Tech_Label = tech_labels[as.character(Technology_ID)],
    Tech_Label_with_share = paste0(Tech_Label, " (", round(Area_Share_percent, 2), "%)"),
    Tech_Label_with_share = factor(Tech_Label_with_share, levels = Tech_Label_with_share[order(Technology_ID)]),
    Label_Type = ifelse(`Area_Share_percent` >= 5, "inside", "outside"),
    Label_Text = paste0(Tech_Label, ": ", round(`Area_Share_percent`, 2), "%")
  ) %>%
  arrange(desc(Tech_Label)) %>%
  mutate(
    cumulative = cumsum(Area_Share_percent),
    midpoint = cumulative - Area_Share_percent / 2
  )

# 统一颜色方案
category_colors <- c(
  "Basalt, 2μm" = "#f8dda4",
  "Basalt, 10μm" = "#f9a03f",
  "Basalt, 20μm" = "#d45113",
  "Basalt, 50μm" = "#813405"
)
# 对应带百分比的标签的颜色
used_colors <- setNames(category_colors[df$Tech_Label], df$Tech_Label_with_share)

# 绘图
ggplot(df, aes(x = "", y = Area_Share_percent, fill = Tech_Label_with_share)) +
  geom_col(width = 1, color = "white") +
  coord_polar("y") +
  
  geom_text(
    data = df %>% filter(Label_Type == "inside" & Area_Share_percent > 0),
    aes(label = paste0(round(`Area_Share_percent`, 1), "%")),
    position = position_stack(vjust = 0.5),
    size = 10,
    color = "white"
  ) +
  scale_fill_manual(values = used_colors, drop = FALSE) +
  labs(fill = "Optimal Grain Size (Basalt)") +
  guides(fill = guide_legend(ncol = 1, title.position = "top")) +
  theme_void(base_size = 15) +
  theme(
    plot.title = element_text(hjust = 0.5),
    strip.text = element_text(size = 23, face = "plain"),
    legend.title = element_text(size = 30),
    legend.text = element_text(size = 30),
    legend.position = "bottom",
    plot.margin = margin(t = 20, r = 10, b = 10, l = 10)
  )

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    ggsave(paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Optimal Material Selection.svg"), width = 8, height = 6)
  } else{
    ggsave(paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Optimal Material Selection.svg"), width = 8, height = 6)
  }
} else {
  if (isTRUE(trade)){
    ggsave(paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Optimal Material Selection.svg"), width = 8, height = 6)
  } else{
    ggsave(paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Optimal Material Selection.svg"), width = 8, height = 6)
  }
}


# ==============================================================================
# PART 2: Bar Chart (包含原图和新增的大区独立图)
# ==============================================================================

#==================== 1. 读入并预处理 ====================

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    df_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/EW_summary_by_region_subregion_technology.csv")
    )
  } else{
    df_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/EW_summary_by_region_subregion_technology.csv")
    )
  }
} else {
  if (isTRUE(trade)){
    df_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/EW_summary_by_region_subregion_technology.csv")
    )
  } else{
    df_raw <- read_csv(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/EW_summary_by_region_subregion_technology.csv")
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

## 技术标签
tech_labels <- c(
  `1` = "Basalt, 2 μm",
  `2` = "Basalt, 10 μm",
  `3` = "Basalt, 20 μm",
  `4` = "Basalt, 50 μm"
)

technology_order <- c(
  "Basalt, 2 μm",
  "Basalt, 10 μm",
  "Basalt, 20 μm",
  "Basalt, 50 μm"
)

## 颜色设置
tech_colors <- c(
  "Basalt, 2 μm"  = "#f8dda4",
  "Basalt, 10 μm" = "#f9a03f",
  "Basalt, 20 μm" = "#d45113",
  "Basalt, 50 μm" = "#813405"
)

df <- df_raw %>%
  mutate(
    Region      = region_labels[as.character(Region_ID)],
    Subregion  = subregion_labels[as.character(Subregion_ID)],
    Technology = tech_labels[as.character(Technology_ID)],
    Technology = factor(Technology, levels = technology_order),
    # ★ km² → 10^6 km²
    Area_1e6_km2 = Total_Area_km2 / 1e6
  ) %>%
  filter(!is.na(Region), !is.na(Subregion), !is.na(Technology)) %>%
  tidyr::complete(tidyr::nesting(Region, Subregion), Technology, fill = list(Area_1e6_km2 = 0))

## 区域顺序
region_order <- c("Asia", "Europe", "Africa", "Americas", "Oceania", "Antarctica")
df$Region <- factor(df$Region, levels = region_order)

#==================== 2. 每个次区域总面积（大图柱顶标注用） ====================

df_sub_totals <- df %>%
  group_by(Region, Subregion, .drop = FALSE) %>%
  summarise(
    Total_1e6_km2 = sum(Area_1e6_km2, na.rm = TRUE),
    .groups = "drop"
  )

#==================== 3. 大图：次区域 × 技术堆积柱状图 ====================

p_sub <- ggplot(
  df,
  aes(x = Subregion, y = Area_1e6_km2, fill = Technology)
) +
  geom_col(color = "black", width = 0.9) +
  # 次区域总面积标注
  geom_text(
    data = df_sub_totals,
    aes(
      x = Subregion,
      y = Total_1e6_km2,
      label = sprintf("%.2f", Total_1e6_km2)
    ),
    vjust = -0.3,
    size  = 5,
    color = "black",
    inherit.aes = FALSE
  ) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  facet_grid(
    ~ Region,
    scales  = "free_x",
    space   = "free_x"   # strip 不再加面积，只显示区域名
  ) +
  scale_fill_manual(
    values = tech_colors,
    breaks = technology_order,
    drop = FALSE
  ) +
  labs(
    x    = NULL,
    y    = expression("Area (" * 10^6 * " km"^2 * ")"),
    fill = "Technology"
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
    legend.position  = c(0.92, 0.8),
    legend.title     = element_blank(),
    legend.text      = element_text(size = 15)
  )

#==================== 4. 小图：区域 × 技术 总面积柱状图 (用于镶嵌) ====================

df_region <- df %>%
  group_by(Region, Technology) %>%
  summarise(
    Area_1e6_km2 = sum(Area_1e6_km2, na.rm = TRUE),
    .groups = "drop"
  )

region_total <- df_region %>%
  group_by(Region) %>%
  summarise(
    Total_1e6_km2 = sum(Area_1e6_km2, na.rm = TRUE),
    .groups = "drop"
  )

# 这个 p_region 是用来放在大图里面的，所以隐藏了图例，字号较小
p_region <- ggplot(df_region,
                   aes(x = Region, y = Area_1e6_km2, fill = Technology)) +
  geom_col(color = "black", width = 0.7) +
  # 区域总面积标注
  geom_text(
    data = region_total,
    aes(
      x = Region,
      y = Total_1e6_km2,
      label = sprintf("%.2f", Total_1e6_km2)
    ),
    vjust = -0.3,
    size  = 4,
    color = "black",
    inherit.aes = FALSE
  ) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.18))) +
  scale_fill_manual(values = tech_colors, drop = FALSE) +
  labs(
    x = NULL,
    y = expression("Area (" * 10^6 * " km"^2 * ")")
  ) +
  theme_classic(base_size = 10) +
  theme(
    axis.text.x = element_text(angle = 0, hjust = 0.5, size = 14),
    axis.text.y = element_text(size = 14),
    axis.title  = element_text(size = 16),
    legend.position = "none",
    plot.margin = margin(2, 2, 2, 2)
  )

#==================== 5. 镶嵌小图并保存组合图 ====================

final_plot <- p_sub +
  inset_element(
    p_region,
    left   = 0.33,
    bottom = 0.40,
    right  = 0.73,
    top    = 0.95,
    align_to = "panel"
  )

print(final_plot)

# 保存组合图
if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_region_subregion_tech_area_1e6km2.svg"),
      final_plot,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_region_subregion_tech_area_1e6km2.svg"),
      final_plot,
      width = 12, height = 7
    )
  }
} else {
  if (isTRUE(trade)){
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_region_subregion_tech_area_1e6km2.svg"),
      final_plot,
      width = 12, height = 7
    )
  } else{
    ggsave(
      paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_region_subregion_tech_area_1e6km2.svg"),
      final_plot,
      width = 12, height = 7
    )
  }
}

#==================== 6. 单独绘制并保存大区柱状图 ====================

# --- 配置项 ---
# 你可以在这里调整图例位置，可选值：
# "right" (右侧), "top" (顶部), "bottom" (底部), 或者坐标 c(0.9, 0.9) (图内右上角)
my_legend_position <- c(0.9, 0.9) 

p_region_standalone <- ggplot(df_region,
                              aes(x = Region, y = Area_1e6_km2, fill = Technology)) +
  geom_col(color = "black", width = 0.65) + # width调整为0.65，让柱子胖瘦适中
  
  # 区域总面积标注 (字体调大，加粗)
  geom_text(
    data = region_total,
    aes(
      x = Region,
      y = Total_1e6_km2,
      label = sprintf("%.2f", Total_1e6_km2)
    ),
    vjust = -0.5,      # 稍微再往上提一点，避免紧贴柱子
    size  = 6.5,       # ★ 字号调大 (大图里是5，这里因为柱子少，可以更大更清晰)
    color = "black",
    # fontface = "bold", # ★ 加粗
    inherit.aes = FALSE
  ) +
  
  # Y轴扩展，防止顶部数字被切掉
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  
  scale_fill_manual(values = tech_colors) +
  
  labs(
    x = NULL, # 大区名字已经很清楚了，不需要X轴标题
    y = expression("Area (" * 10^6 * " km"^2 * ")"),
    fill = "Technology"
  ) +
  
  # 使用 classic 主题，基础字号直接设为 18 (与大图接近)
  theme_classic(base_size = 18) +
  
  theme(
    # X轴文字：大区名字 (Asia, Europe...)
    axis.text.x = element_text(
      size = 22,        # ★ 字号加大
      color = "black", 
      # face = "bold",    # 加粗
      margin = margin(t = 8) # 增加与X轴线的距离
    ),
    
    # Y轴文字：刻度数值
    axis.text.y = element_text(
      size = 20,        # ★ 字号加大
      color = "black"
    ),
    
    # Y轴标题：Area (...)
    axis.title.y = element_text(
      size = 24,        # ★ 标题字号更大
      face = "bold", 
      margin = margin(r = 15) # 增加与Y轴的距离
    ),
    
    # 图例设置
    legend.position = my_legend_position, 
    legend.title = element_blank(), # 图例标题
    legend.text  = element_text(size = 18),                # 图例内容
    legend.key.size = unit(1, "cm"),                       # 图例色块大一点
    
    # 整个图片的边距 (上 右 下 左)
    plot.margin = margin(t = 20, r = 20, b = 20, l = 20)
  )

# --- 保存逻辑 ---
# 调整 width 和 height 来控制长宽比
# width = 10, height = 7 看起来会比较舒展 (类似大图的比例)

save_width <- 12
save_height <- 6

if (isTRUE(maxcb)){
  if (isTRUE(trade)){
    save_path <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_withtrade/Map/Global_ERW_Region_Only_tech_area_1e6km2.svg")
  } else{
    save_path <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/maxclimatebenefit_notrade/Map/Global_ERW_Region_Only_tech_area_1e6km2.svg")
  }
} else {
  if (isTRUE(trade)){
    save_path <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_withtrade/Map/Global_ERW_Region_Only_tech_area_1e6km2.svg")
  } else{
    save_path <- paste0("E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/", start_year, "/mincost_notrade/Map/Global_ERW_Region_Only_tech_area_1e6km2.svg")
  }
}

ggsave(save_path, p_region_standalone, width = save_width, height = save_height)

print(paste("Saved Region-only chart to:", save_path))
