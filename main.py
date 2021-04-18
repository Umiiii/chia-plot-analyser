from job import Job
import os
import time
from tabulate import tabulate
import argparse

PATH = "/Users/umi/logs"

def cls():
    os.system("clear")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display logs')
    parser.add_argument('--config_dir', 
                        help='config_dir')
    args = parser.parse_args()
    PATH = args.config_dir
    while True:
        colmn = ["logfile","plot_id","stage","phase1","phase2","phase3","phase4","total"]
        result = []
        for dirpath,dirnames,filenames in os.walk(PATH):
            for filename in filenames:
                logfile = os.path.join(dirpath,filename)
                j = Job(os.path.join(dirpath,logfile))
                result.append([j.logfile, j.plot_id, j.phase, j.elapsed_time[0], j.elapsed_time[1], j.elapsed_time[2], j.elapsed_time[3], j.total_time])
            print(tabulate(result,colmn,tablefmt="fancy_grid"))
        time.sleep(60)
        cls()