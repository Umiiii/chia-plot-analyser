from datetime import datetime
import argparse
import os
import re
import time

class Job:

    # These are constants, not updated during a run.
    k = 0
    r = 0
    u = 0
    b = 0
    n = 0  # probably not used
    tmpdir = ''
    tmp2dir = ''
    dstdir = ''
    logfile = ''
    jobfile = ''
    job_id = 0
    plot_id = '--------'

    # These are dynamic, cached, and need to be udpated periodically
    phase = (None, None)   # Phase/subphase
    elapsed_time = [0,0,0,0]
    phase_date = ["","","",""]
    total_time = 0
 
    def __init__(self, logfile):
        self.logfile = logfile
        self.init_from_logfile()


    def init_from_logfile(self):
        '''Read plot ID and job start time from logfile.  Return true if we
           find all the info as expected, false otherwise'''
        assert self.logfile
        # Try reading for a while; it can take a while for the job to get started as it scans
        # existing plot dirs (especially if they are NFS).
        found_id = False
        found_log = False
        found_tmp = False
        found_plot_size = False
        found_buffer = False
        found_bucket = False
        found_threads = False
        for attempt_number in range(3):
            with open(self.logfile, 'r') as f:
                for line in f:
                    m = re.match('^ID: ([0-9a-f]*)', line)
                    if m:
                        self.plot_id = m.group(1)
                        found_id = True
                    m = re.match('^Starting plotting progress into temporary dirs: (.*) and (.*)', line)
                    if m:
                        self.tmpdir = m.group(1)
                        self.tmp2dir = m.group(2)

                    m = re.match('^Plot size is: (.*)', line)
                    if m:
                        self.k = m.group(1)

                    m = re.match('^Buffer size is: (.*)', line)
                    if m:
                        self.b = m.group(1)

                    m = re.match('^Using (.*) buckets', line)
                    if m:
                        self.u = m.group(1)

                    m = re.match('^Using (.*) threads of stripe size (.*)', line)
                    if m:
                        self.r = m.group(1)

                    m = re.match(r'^Starting phase 1/4:.*\.\.\. (.*)', line)
                    if m:
                        # Mon Nov  2 08:39:53 2020
                        self.start_time = datetime.strptime(m.group(1), '%a %b  %d %H:%M:%S %Y')
                        found_log = True
                        break  # Stop reading lines in file

            if found_id and found_log:
                break  # Stop trying
            else:
                time.sleep(1)  # Sleep and try again

        # If we couldn't find the line in the logfile, the job is probably just getting started
        # (and being slow about it).  In this case, use the last metadata change as the start time.
        # TODO: we never come back to this; e.g. plot_id may remain uninitialized.
        if not found_log:
            self.start_time = datetime.fromtimestamp(os.path.getctime(self.logfile))

        # Load things from logfile that are dynamic
        self.update_from_logfile()

    def update_from_logfile(self):
        self.set_phase_from_logfile()

    def set_phase_from_logfile(self):
        assert self.logfile

        # Map from phase number to subphase number reached in that phase.
        # Phase 1 subphases are <started>, table1, table2, ...
        # Phase 2 subphases are <started>, table7, table6, ...
        # Phase 3 subphases are <started>, tables1&2, tables2&3, ...
        # Phase 4 subphases are <started>
        phase_subphases = {}

        with open(self.logfile, 'r') as f:
            for line in f:
                # "Starting phase 1/4: Forward Propagation into tmp files... Sat Oct 31 11:27:04 2020"
                m = re.match(r'^Starting phase (\d).*', line)
                if m:
                    phase = int(m.group(1))
                    phase_subphases[phase] = 0

                # Phase 1: "Computing table 2"
                m = re.match(r'^Computing table (\d).*', line)
                if m:
                    phase_subphases[1] = max(phase_subphases[1], int(m.group(1)))

                # Phase 2: "Backpropagating on table 2"
                m = re.match(r'^Backpropagating on table (\d).*', line)
                if m:
                    phase_subphases[2] = max(phase_subphases[2], 7 - int(m.group(1)))

                # Phase 3: "Compressing tables 4 and 5"
                m = re.match(r'^Compressing tables (\d) and (\d).*', line)
                if m:
                    phase_subphases[3] = max(phase_subphases[3], int(m.group(1)))

                # TODO also collect timing info:

                # "Time for phase 1 = 22796.7 seconds. CPU (98%) Tue Sep 29 17:57:19 2020"
                for phase in range(4):
                    m = re.match(r'^Time for phase ' + str(phase+1) + ' = (\d+.\d+) seconds..*', line)
                    if m:
                        self.elapsed_time[phase] = m.group(1)

                # Total time = 49487.1 seconds. CPU (97.26%) Wed Sep 30 01:22:10 2020
                m = re.match(r'^Total time = (\d+.\d+) seconds.*', line)
                if m:
                    self.total_time = m.group(1)

        if phase_subphases:
            phase = max(phase_subphases.keys())
            self.phase = (phase, phase_subphases[phase])
        else:
            self.phase = (0, 0)

    def progress(self):
        '''Return a 2-tuple with the job phase and subphase (by reading the logfile)'''
        return self.phase

    def plot_id_prefix(self):
        return self.plot_id[:8]

    # TODO: make this more useful and complete, and/or make it configurable
    def status_str_long(self):
        return '{plot_id}\nk={k} r={r} b={b} u={u}\ntmp:{tmp}\ntmp2:{tmp2}\ndst:{dst}\nlogfile:{logfile}'.format(
            plot_id = self.plot_id,
            k = self.k,
            r = self.r,
            b = self.b,
            u = self.u,
            tmp = self.tmpdir,
            tmp2 = self.tmp2dir,
            dst = self.dstdir,
            plotid = self.plot_id,
            logfile = self.logfile
            )

    def get_mem_usage(self):
        return self.proc.memory_info().vms  # Total, inc swapped

    def get_tmp_usage(self):
        total_bytes = 0
        with os.scandir(self.tmpdir) as it:
            for entry in it:
                if self.plot_id in entry.name:
                    try:
                        total_bytes += entry.stat().st_size
                    except FileNotFoundError:
                        # The file might disappear; this being an estimate we don't care
                        pass
        return total_bytes

    def get_run_status(self):
        '''Running, suspended, etc.'''
        status = self.proc.status()
        if status == psutil.STATUS_RUNNING:
            return 'RUN'
        elif status == psutil.STATUS_SLEEPING:
            return 'SLP'
        elif status == psutil.STATUS_DISK_SLEEP:
            return 'DSK'
        elif status == psutil.STATUS_STOPPED:
            return 'STP'
        else:
            return self.proc.status()

    def get_time_wall(self):
        return int((datetime.now() - self.start_time).total_seconds())

    def get_time_user(self):
        return int(self.proc.cpu_times().user)

    def get_time_sys(self):
        return int(self.proc.cpu_times().system)

    def get_time_iowait(self):
        return int(self.proc.cpu_times().iowait)

    def suspend(self, reason=''):
        self.proc.suspend()
        self.status_note = reason

    def resume(self):
        self.proc.resume()

    def get_temp_files(self):
        temp_files = []
        for f in self.proc.open_files():
            if self.tmpdir in f.path or self.tmp2dir in f.path or self.dstdir in f.path:
                temp_files.append(f.path)
        return temp_files


if __name__ == "__main__":
    l = Job("./logs.txt")
    print(l.status_str_long())