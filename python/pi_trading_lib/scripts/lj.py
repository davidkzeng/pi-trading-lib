import os

import pi_trading_lib.work_dir as work_dir


def main():
    sim_dir = os.path.join(work_dir.get_work_dir(), 'sim')
    date_subdirs = [os.path.join(sim_dir, d) for d in os.listdir(sim_dir)]
    sim_subdirs = []
    for ds in date_subdirs:
        sim_subdirs.extend([os.path.join(ds, d) for d in os.listdir(ds)])
    latest_sim_dir = max(sim_subdirs, key=os.path.getmtime)
    print(latest_sim_dir)


if __name__ == "__main__":
    main()
