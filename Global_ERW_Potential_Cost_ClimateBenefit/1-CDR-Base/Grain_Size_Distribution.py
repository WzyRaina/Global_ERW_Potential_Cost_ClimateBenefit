# 根据对数正态分布的粒径分布，给定标准差，推得2、10、20、50μm粒径分布

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os


def generate_psd_for_multiple_p80(
        sigma,
        save_folder='E:/wzy/1-CDR-Base/EW/Output/Grain Size Distribution/',
        plot=True,
        uncertainty=False
):
    """
    根据对数正态分布生成多个P80的PSD。

    1. 无论 uncertainty 为真假，函数都会返回包含所有结果的字典 psd_dict。
    2. 仅当 uncertainty=False 时，才会将结果保存为 CSV 文件至 save_folder。

    Parameters
    ----------
    sigma : float
        对数正态分布的标准差
    save_folder : str
        存储csv的文件夹
    plot : bool
        是否绘制曲线
    uncertainty : bool
        是否为不确定性分析模式（True时不保存文件）

    Returns
    -------
    psd_dict : dict
        {p80_value: pd.DataFrame}，包含各粒径的分布数据
    """

    p80_list = [2, 10, 20, 50]

    # 默认14个离散粒径
    d_values = np.array([
        0.1, 1, 2, 5, 10, 20,
        30, 40, 50, 60, 70,
        80, 90, 100
    ])  # μm

    psd_dict = {}

    # 准备绘图
    if plot:
        plt.figure(figsize=(8, 5))

    for p80 in p80_list:
        # 计算 μ
        z_p80 = 0.8416
        mu = np.log(p80) - z_p80 * sigma

        # 计算 pdf
        pdf = (1 / (d_values * sigma * np.sqrt(2 * np.pi))) * np.exp(- (np.log(d_values) - mu) ** 2 / (2 * sigma ** 2))

        # 归一化为质量分数
        fraction = pdf / pdf.sum()

        df = pd.DataFrame({
            'Diameter': d_values,
            'Fraction': fraction
        })

        # === 始终将结果存入字典，方便函数返回 ===
        psd_dict[p80] = df

        # === 仅当 uncertainty 为 False 时，保存文件 ===
        if not uncertainty:
            # 确保文件夹存在
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)

            save_path = os.path.join(save_folder, f'Grain Size Distribution ({int(p80)} μm).csv')
            df.to_csv(save_path, index=False, encoding='utf-8-sig')
            # print(f'已保存：{save_path}')

        # 绘图
        if plot:
            plt.plot(d_values, fraction, label=f'P80 = {p80} μm')

    if plot:
        plt.xscale('log')
        plt.xlabel('Diameter (μm)')
        plt.ylabel('Fraction')
        plt.legend()
        plt.title(f'Log-Normal PSDs (σ = {sigma})')
        plt.tight_layout()
        plt.show()

        # === 始终返回数据字典 ===
    return psd_dict

if __name__ == "__main__":
    result_dict = generate_psd_for_multiple_p80(
        sigma=0.5,
        save_folder='E:/wzy/1-CDR-Base/EW/Output/Grain Size Distribution/',
        plot=True,
        uncertainty=False
    )

    # 打印查看返回结果的一个示例
    print("函数返回了字典，包含 keys:", result_dict.keys())
    print("2μm 的数据预览:\n", result_dict[2].head())
