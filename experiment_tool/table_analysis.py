# df_temp = df_temp.sort_values(by=['conf_id'])
# df_temp = df_temp[(df_temp["conf_id"] != "UbiComp") | (df_temp["patent_year"] >= 2005 )]
import seaborn as sns
import matplotlib.pyplot as plt
# plt_ = sns.lineplot(x="patent_year", y="patent_paper_lag", hue="conf_id", data=df_temp)
for ylable in ["Textual Plan", "Visual Plan", "Multimodal Plan"]:        
    plt_ = sns.lineplot(data=([1, 2, 3, 4], [1, 4, 9, 16]))
    plt.ylabel(ylable,fontsize = 20)
    plt.title('Pefromance over Step Length',fontsize = 20)
    # plt.xticks(rotation=45, fontsize = 20)
    plt.yticks([0,5,10,15,20],fontsize = 20)
    plt.ylim(0, 20)
    plt.legend(fontsize =15, loc = 'upper left')
    plt.xlabel('Step Length', fontsize =20)
    plt.savefig(f'paper_assets/{ylable}.png', bbox_inches = "tight")
    fig = plt.figure()