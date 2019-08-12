import matplotlib.pyplot as plot
import matplotlib.cbook as cbook


def violin_box_plot(to_plot):

    fig = plot.figure(1, figsize=(9, 6)) 
    ax = fig.add_subplot(111) 
    parts=ax.violinplot(to_plot, showmeans=False, showmedians=False, showextrema=False) 
    for pc in parts['bodies']: 
        pc.set_facecolor('xkcd:lightblue') 
        pc.set_edgecolor('xkcd:blue') 
        pc.set_alpha(1) 
        pc.set_linewidth(2) 
    
    medianprops = dict(linestyle='-.', linewidth=2.5, color='firebrick') 
    stats = cbook.boxplot_stats(to_plot)
    flierprops = dict(marker='o', markerfacecolor='green', markersize=12, linestyle='none')  
    ax.set_axisbelow(True) 
    plot.gca().yaxis.grid(True, ls='-', color='white')
    ax.bxp(stats, flierprops=flierprops, medianprops=medianprops)
    ax.set_xticks([])
    ax.set_xticklabels([])
    ax.tick_params(axis='y', length=0)
    ax.set_facecolor('lightgrey')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    plot.savefig('/home/fsforazz/Desktop/hd_cheng_cv.png')
    plot.close()