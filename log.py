from job import Job
import os
def read_log(log_path="/home/umi/logs"):
	result = []
	for dirpath,dirnames,filenames in os.walk(log_path):
	    for filename in filenames:
	        logfile = os.path.join(dirpath,filename)
	        s = os.path.getsize(logfile)
	        if s == 0:
	            continue
	        j = Job(os.path.join(dirpath,logfile))
	        result.append({"plot_id":j.plot_id,"phase":j.phase,"elapsed_time":j.elapsed_time})
	return result

if __name__ == "__main__":
	print(read_log("../logs"))