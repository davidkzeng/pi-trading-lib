"""Used to manually tag contract resolutions

This can happen for a few reasons
1. Contract resolved at a price far from 0, 1
2. Missing market data
"""

import typing as t

CONTRACT_RESOLUTIONS: t.Dict[int, float] = {
    # ========================== 2020 Election ==========================
    23733: 1.0,  # 6900 2020-09-30 NC Unaffiliated absentees on 9/30? 82,000 - 86,000 0.97 0.94 0.99
    24112: 1.0,  # 6942 2020-11-03 NC Republican absentees on 11/3? 1.45 M - 1.475 M 0.86 0.78 0.87
    24113: 0.0,  # 6942 2020-11-03 NC Republican absentees on 11/3? 1.425 M - 1.45 M 0.11 0.12 0.23
    24117: 0.0,  # 6942 2020-11-03 NC Republican absentees on 11/3? 1.475 M - 1.5 M 0.03 0.01 0.04
    23862: 0.0,  # 6920 2020-11-04 Trump winning at 6 a.m. on November 4? 0.41 0.39 0.41
    16006: 0.0,  # 5599 2020-11-17 Which party will win NC in 2020? Democratic 0.05 0.02 0.05
    17018: 0.0,  # 5809 2020-11-17 Which party will win AZ Senate special? Republican 0.03 0.03 0.04
    23692: 0.0,  # 6893 2020-11-17 Which party will win VA-02? Republican 0.03 0.02 0.04
    23850: 0.0,  # 6917 2020-11-17 Which party will win IA-03? Republican 0.03 0.03 0.04
    23926: 1.0,  # 6927 2020-11-17 Florida presidential vote margin? GOP by 3% to 4% 0.98 0.97 0.98
    14248: 1.0,  # 5253 2020-11-23 Which party will win GA-07? Democratic 0.99 0.96 0.99
    14249: 0.0,  # 5253 2020-11-23 Which party will win GA-07? Republican 0.04 0.04 0.05
    24408: 1.0,  # 6985 2020-11-23 Timing of GSA "ascertainment"? Nov. 23 - 0.95 0.94 0.95
    24409: 0.0,  # 6985 2020-11-23 Timing of GSA "ascertainment"? Nov. 24 - Nov. 30 0.05 0.04 0.06
    15772: 0.0,  # 5554 2020-11-24 Trump win popular vote in 2020? 0.08 0.07 0.08
    22040: 0.0,  # 6576 2020-11-25 Which party will win the MI Senate race? Republican 0.05 0.04 0.05
    22041: 1.0,  # 6576 2020-11-25 Which party will win the MI Senate race? Democratic 0.96 0.96 0.97
    24004: 0.0,  # 6934 2020-11-25 North Carolina presidential vote margin? GOP by 6% + 0.03 0.01 0.04
    15704: 0.0,  # 5543 2020-12-15 Which party will win PA in 2020? Republican 0.05 0.05 0.06
    15705: 1.0,  # 5543 2020-12-15 Which party will win PA in 2020? Democratic 0.95 0.95 0.96
    15708: 0.0,  # 5545 2020-12-15 Which party will win MI in 2020? Republican 0.05 0.05 0.07
    15709: 1.0,  # 5545 2020-12-15 Which party will win MI in 2020? Democratic 0.96 0.94 0.95
    15999: 0.0,  # 5596 2020-12-15 Which party will win AZ in 2020? Republican 0.05 0.05 0.06
    16000: 1.0,  # 5596 2020-12-15 Which party will win AZ in 2020? Democratic 0.94 0.94 0.95
    16009: 0.0,  # 5601 2020-12-15 Which party will win NV in 2020? Republican 0.06 0.05 0.06
    16010: 1.0,  # 5601 2020-12-15 Which party will win NV in 2020? Democratic 0.96 0.94 0.95
    16015: 0.0,  # 5604 2020-12-15 Which party will win GA in 2020? Republican 0.06 0.06 0.07
    16016: 1.0,  # 5604 2020-12-15 Which party will win GA in 2020? Democratic 0.94 0.94 0.95
    22282: 1.0,  # 6642 2020-12-15 Pop. vote winner wins Electoral College? 0.95 0.94 0.95
    22809: 0.0,  # 6724 2020-12-15 Trump wins any state he lost in 2016? 0.06 0.05 0.06
    22832: 1.0,  # 6727 2020-12-15 Trump loses any state he won in 2016? 0.96 0.95 0.96
    23959: 0.0,  # 6930 2020-12-15 Georgia presidential vote margin? GOP by 6% + 0.04 0.04 0.05
    23960: 1.0,  # 6930 2020-12-15 Georgia presidential vote margin? Dems by under 1% 0.95 0.95 0.96
    24099: 0.0,  # 6941 2020-12-15 Pennsylvania presidential vote margin? GOP by 3% + 0.04 0.04 0.05
    24101: 1.0,  # 6941 2020-12-15 Pennsylvania presidential vote margin? Dems by 1% to 2% 0.96 0.94 0.96
    24124: 0.0,  # 6943 2020-12-15 Arizona presidential vote margin? GOP by 5% + 0.03 0.03 0.04
    24125: 1.0,  # 6943 2020-12-15 Arizona presidential vote margin? Dems by under 1% 0.95 0.94 0.95
    24177: 1.0,  # 6950 2020-12-15 Georgia presidential vote margin? Biden 10K - 12.5K 0.95 0.94 0.95
    24183: 0.0,  # 6950 2020-12-15 Georgia presidential vote margin? Trump 10K or more 0.04 0.04 0.05
    24238: 0.0,  # 6956 2020-12-15 Will Trump win PA, AZ or GA? 0.07 0.07 0.08
    24297: 0.0,  # 6963 2020-12-15 Will there be a recount in Arizona? 0.05 0.05 0.06
    24318: 0.0,  # 6968 2020-12-15 Will there be a recount in Wisconsin? 0.04 0.03 0.04
    24327: 0.0,  # 6969 2020-12-15 Pennsylvania presidential vote margin? Trump by 15K + 0.08 0.06 0.08
    24328: 1.0,  # 6969 2020-12-15 Pennsylvania presidential vote margin? Biden 75K to 90K 0.94 0.93 0.94
    24467: 1.0,  # 6995 2020-12-15 Biden's margin in GA shrinks by 100+? 0.93 0.94 0.96
    4389: 0.0,  # 2721 2020-12-18 Which party wins the Presidency in 2020? Republican 0.07 0.07 0.08
    4390: 1.0,  # 2721 2020-12-18 Which party wins the Presidency in 2020? Democratic 0.94 0.93 0.94
    7940: 1.0,  # 3698 2020-12-18 2020 presidential election winner? Biden 0.94 0.94 0.95
    7943: 0.0,  # 3698 2020-12-18 2020 presidential election winner? Trump 0.06 0.06 0.07
    9149: 1.0,  # 4036 2020-12-18 Woman VP in 2020? 0.93 0.92 0.93
    18036: 1.0,  # 5960 2020-12-18 SC primary winner elected president? 0.94 0.93 0.94
    18037: 1.0,  # 5961 2020-12-18 TX Dem primary winner elected president? TX primary winner elected president? 0.94 0.93 0.94
    18039: 1.0,  # 5963 2020-12-18 MA primary winner elected president? 0.94 0.93 0.94
    22318: 1.0,  # 6653 2020-12-21 Electoral College margin of victory? Dems by 60 - 99 0.97 0.96 0.97
    24298: 0.0,  # 6964 2020-12-21 Will Trump win MI, WI or NV? 0.04 0.03 0.04
    24352: 1.0,  # 6974 2020-12-21 Wisconsin presidential vote margin? Biden 20K to 25K 0.97 0.97 0.98
    24469: 0.0,  # 6996 2020-12-21 Biden's margin in WI shrinks by 100+? 0.04 0.03 0.04
    24497: 1.0,  # 6998 2020-12-21 Electoral college votes for Biden? 306 0.96 0.96 0.97
    24503: 0.0,  # 6998 2020-12-21 Electoral college votes for Biden? 293 or fewer 0.05 0.04 0.05
    24512: 0.0,  # 6999 2020-12-21 Electoral college votes for Trump? 245 or more 0.04 0.03 0.04
    # ========================== Election objection, unclear rules, missing PI market data ==========================
    24625: 1.0,  # 7023 2021-01-07 Johnson objects to any election results? 0.91 0.91 0.93
    24633: 0.0,  # 7025 2021-01-07 Senators objecting to election results? Two 0.19 0.06 0.18
    24638: 1.0,  # 7025 2021-01-07 Senators objecting to election results? Seven 0.92 0.89 0.92
    24642: 0.0,  # 7026 2021-01-07 House members objecting to election? 1 to 3 0.04 0.01 0.02
    24652: 0.0,  # 7028 2021-01-07 Tuberville objects to election results? 0.04 0.03 0.05
    # ========================== Unclear resolution ===============================
    19795: 0.0,  # 6234 2021-01-14 2020 hottest on record per NASA? 0.09 0.08 0.09
    # ========================== ? ==========================
    25810: 1.0,  # 7223 2021-04-29 ICE Director Nominee by May 31? 0.8 0.83 0.84
    # ========================== Missing PredictIt market data ==========================
    26063: 0.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 81 or fewer 0.2 0.2 0.23
    26064: 0.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 84 or 85 0.16 0.11 0.22
    26065: 1.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 88 or 89 0.1 0.09 0.15
    26067: 0.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 86 or 87 0.05 0.1 0.19
    26068: 0.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 98 or more 0.31 0.2 0.32
    26069: 0.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 90 or 91 0.03 0.02 0.06
    26070: 0.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 92 or 93 0.04 0.03 0.07
    26071: 0.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 94 or 95 0.01 0.0 0.05
    26072: 0.0,  # 7260 2021-05-12 Votes for Graves at Commerce by 6/15? 82 or 83 0.16 0.16 0.18
    26126: 1.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 159 or fewer  0.22 0.21 0.28
    26127: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 160 to 164 0.04 0.02 0.04
    26128: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 165 to 169 0.04 0.03 0.04
    26129: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 170 to 174 0.05 0.04 0.17
    26130: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 175 to 179 0.05 0.04 0.05
    26131: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 180 to 184 0.06 0.06 0.21
    26132: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 185 to 189 0.06 0.06 0.25
    26133: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 190 to 194 0.0 0.06 0.14
    26134: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 195 to 199 0.05 0.05 0.14
    26135: 0.0,  # 7267 2021-05-12 Votes to install Stefanik by May 21? 200 or more 0.26 0.24 0.26
}

UNRESOLVED_CONTRACTS = set([
    24699, 24700, 24701, 24702, 24703, 24704 # Market 7038, cancelled market
])

NO_CORRECT_CONTRACT_MARKETS = set([
    # ===================== Biden Sec Confirms =======================
    6951,  # Secretary of Labor on Mar. 1?, 0 correct contracts
    6952,  # Attorney General on Mar. 1?, 0 correct contracts
    6958,  # HUD Secretary on Mar. 1?, 0 correct contracts
    6965,  # HHS Secretary on Mar. 1?, 0 correct contracts
    6966,  # Commerce Secretary on Mar. 1?, 0 correct contracts
    6976,  # Interior Secretary on March 1?, 0 correct contracts
    6977,  # CIA Director on March 1?, 0 correct contracts
    6978,  # Secretary of Education on Mar. 1?, 0 correct contracts
    6981,  # EPA Administrator on March 1?, 0 correct contracts
    6992,  # OMB Director on March 1?, 0 correct contracts
    6993,  # USTR on March 1?, 0 correct contracts
    7020,  # USAID Administrator on March 1?, 0 correct contracts
    7038,  # Who'll win VA GOP gubernatorial primary?, 0 correct contracts
])
