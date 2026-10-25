#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISPhO 2025 Theoretical Problem 1 — "Ferromagnetic domain wall dynamics"
Ferromagnetic Simulator — the organisers' program in one file.

The official SOFTWARE folder (app.py, panel.py, plots.py, server.py,
files.py, auxil.py, config.py, c_initial.py) put together without changing
how it works: the same window, the same LLG integration with
scipy.integrate.solve_ivp, the same 200 saved time points and the same
.ispho files, so files saved here open in the original and back.
Only the warning text is translated in the Korean edition; the window keeps
the English labels the problem sheet quotes (Solve, Plot, Save, Load).

    python ispho2025_T1_ferro_sim.py        (needs numpy, scipy, matplotlib)
"""

LANG = "KO"          # build_editions.py rewrites this line for the KO edition

MSG = {
 "EN": {"perm": ("Permission denied",
                 "This file is opened externally. Ensure you have closed all other "
                 "apps that may be using this file."),
        "save": "Save file as", "open": "Open *.ispho"},
 "KO": {"perm": ("권한 없음",
                 "이 파일을 다른 프로그램이 열고 있습니다. 이 파일을 쓰고 있을 수 있는 "
                 "다른 프로그램을 모두 닫았는지 확인하세요."),
        "save": "다른 이름으로 저장", "open": "*.ispho 열기"},
}[LANG]

# python imports
import json
import tkinter as tk
from copy import deepcopy
from sys import stderr  # Debug stream
from tkinter import Widget, filedialog, messagebox, ttk
from types import SimpleNamespace
from typing import Literal

import numpy as np
from numpy import array
from scipy.integrate import solve_ivp

# MPL and stuff
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


# ═════════════════════════════════ config.py ═════════════════════════════════
config = SimpleNamespace(
    tasks=["B", "C"],
    task="B",
    B={"alpha": None, "beta": None, "b": None, "T": None},
    C={"alpha": None, "beta": None, "b": None, "T": None, "L": None},
    t=None,
    solution_B=None,
    solution_C=None,
    full_progress=200,
)


# ═════════════════════════════════ c_initial.py ══════════════════════════════
# the relaxed wall for task C (beta = 100, 250 cells), as shipped
init = array((
    0.01346676159023258, -4.687942732164412e-06, 0.9999093190159982,
    0.01488139184286974, -4.666760981740164e-06, 0.9998892659200574,
    0.016447283643256812, -4.777732422393785e-06, 0.9998647342452235,
    0.0181751683081038, -4.755763566371299e-06, 0.9998348179504579,
    0.02008708766847605, -4.862347424007824e-06, 0.9997982340648619,
    0.02219743485828572, -4.839813513287396e-06, 0.9997536065543494,
    0.024531827175967868, -4.9417525726506265e-06, 0.9996990494090039,
    0.02710907438726112, -4.918859933813393e-06, 0.9996324814761511,
    0.029959186800452998, -5.0158939416218065e-06, 0.9995511227864579,
    0.03310630053033068, -4.992825005445103e-06, 0.9994518361606946,
    0.03658580480556199, -5.084683995099628e-06, 0.9993305153089207,
    0.04042825242721589, -5.061585837768679e-06, 0.9991824439754924,
    0.04467559144986619, -5.147979776035566e-06, 0.9990015472824827,
    0.049366086706838515, -5.124947770692318e-06, 0.9987807514312844,
    0.05454964083571079, -5.205550708031113e-06, 0.9985110598446414,
    0.060273748139826805, -5.182604928621357e-06, 0.9981818848459646,
    0.06659788708318226, -5.2570309610404295e-06, 0.9977798962629262,
    0.07358051892371845, -5.234081891311393e-06, 0.9972892795910782,
    0.08129252575292843, -5.301848977664802e-06, 0.9966902854999463,
    0.08980524971279828, -5.278647534996282e-06, 0.9959593450935277,
    0.09920293287103929, -5.339123424173335e-06, 0.9950672228878386,
    0.10957176218674125, -5.315188180576566e-06, 0.9939788875468868,
    0.12101123208739588, -5.367510258251291e-06, 0.9926511379468204,
    0.1336241050598368, -5.342021943624999e-06, 0.9910320875264234,
    0.1475265514326928, -5.384979663533371e-06, 0.9890580956562302,
    0.16283883821831088, -5.356629663435766e-06, 0.986652680901409,
    0.1796939821973767, -5.388494644429127e-06, 0.9837225588167509,
    0.1982288142023674, -5.355270864925904e-06, 0.9801557718976218,
    0.21859068098766116, -5.3735567597178545e-06, 0.9758166396154282,
    0.24092826434069867, -5.3324487586428125e-06, 0.9705429261027427,
    0.2653955504538027, -5.333583486859848e-06, 0.9641396173616924,
    0.2921413840083626, -5.280193628568048e-06, 0.9563751417294255,
    0.32130947930534265, -5.2590970729675985e-06, 0.9469742438301332,
    0.35302518210870043, -5.187165175816294e-06, 0.9356138203166698,
    0.38738981446591714, -5.136759181942508e-06, 0.9219160111525796,
    0.4244627016527202, -5.037662447545378e-06, 0.9054454234676597,
    0.4642479968944935, -4.948419647413801e-06, 0.8857052542203546,
    0.506670335465589, -4.81082454593618e-06, 0.8621398791002143,
    0.5515534457616107, -4.670617123185033e-06, 0.834139554538574,
    0.5985901951415649, -4.4806598040188656e-06, 0.8010554152239721,
    0.6473165324043751, -4.275408001194955e-06, 0.7622212978244577,
    0.6970831728418286, -4.018038217614716e-06, 0.7169902719871902,
    0.7470374191793923, -3.7338922909952825e-06, 0.6647819900776428,
    0.7961147284008373, -3.396144549964228e-06, 0.6051457173371955,
    0.8430524144459083, -3.023843548999844e-06, 0.5378314108414082,
    0.8864280231754721, -2.6003332316835825e-06, 0.4628664599237957,
    0.9247301044048039, -2.14140057424556e-06, 0.3806234806246834,
    0.9564584415597605, -1.6407438336597407e-06, 0.29186854843637816,
    0.9802479871067835, -1.113049125940043e-06, 0.19777230284306707,
    0.9949999947961695, -5.615611620633712e-07, 0.09987497361854465,
    1.0, 1.3992947976911144e-10, -3.888164662874127e-11,
    0.9949999947944421, 5.617702632135909e-07, -0.09987497363575149,
    0.9802479870925346, 1.1133186317116228e-06, -0.19777230291368997,
    0.9564584415600882, 1.640924441041474e-06, -0.29186854843530347,
    0.9247301043833376, 2.1416409147183864e-06, -0.38062348067683505,
    0.8864280231918543, 2.600460136041371e-06, -0.46286645989242203,
    0.843052414427199, 3.024040803089251e-06, -0.5378314108707344,
    0.7961147284499817, 3.3961978568324543e-06, -0.6051457172725424,
    0.7470374191711399, 3.734038626495476e-06, -0.6647819900869159,
    0.6970831729376319, 4.0180037508461314e-06, -0.7169902718940477,
    0.6473165324085586, 4.27550119426594e-06, -0.7622212978209052,
    0.5985901952920136, 4.480528383570849e-06, -0.8010554151115508,
    0.5515534457735826, 4.670659217379917e-06, -0.8341395545306589,
    0.5066703356720873, 4.81059090170783e-06, -0.8621398789788602,
    0.4642479969037781, 4.948415553000098e-06, -0.8857052542154898,
    0.4244627019108323, 5.037324283742008e-06, -0.9054454233466638,
    0.3873898144576115, 5.136715652895396e-06, -0.9219160111560726,
    0.3530251824093872, 5.186722580924467e-06, -0.9356138202032207,
    0.3213094792614669, 5.259022162953382e-06, -0.9469742438450246,
    0.2921413843392307, 5.2796488113253745e-06, -0.9563751416283639,
    0.26539555035439594, 5.333486401697487e-06, -0.9641396173890617,
    0.24092826468711573, 5.331806013893084e-06, -0.9705429260167578,
    0.21859068081165742, 5.373447970978271e-06, -0.9758166396548625,
    0.19822881454845653, 5.354536670797436e-06, -0.9801557718276405,
    0.17969398192336247, 5.388386138390109e-06, -0.9837225588668147,
    0.16283883854787942, 5.355812827921466e-06, -0.9866526808470321,
    0.14752655103963425, 5.384885225002268e-06, -0.9890580957148714,
    0.13362410535728722, 5.341133740228563e-06, -0.9910320874863362,
    0.12101123155538808, 5.367445717359621e-06, -0.9926511380116924,
    0.10957176243798916, 5.314242427710435e-06, -0.9939788875192134,
    0.09920293218209601, 5.339106816146887e-06, -0.9950672229565426,
    0.08980524990620166, 5.277660585320763e-06, -0.9959593450761158,
    0.08129252489180652, 5.301900580083865e-06, -0.9966902855702057,
    0.07358051905100704, 5.233072504982376e-06, -0.9972892795817189,
    0.06659788603821953, 5.257173185458087e-06, -0.9977798963327019,
    0.06027374819700863, 5.181594010951871e-06, -0.9981818848425491,
    0.054549639599645726, 5.20580783022905e-06, -0.9985110599122026,
    0.049366086695053615, 5.123957961647322e-06, -0.99878075143191,
    0.044675590020603395, 5.148377498251493e-06, -0.999001547346439,
    0.04042825235350383, 5.060640946766041e-06, -0.9991824439785245,
    0.03658580318684463, 5.085248839394905e-06, -0.9993305153682279,
    0.03310630040827578, 4.991949292550448e-06, -0.999451836164794,
    0.02995918500240351, 5.016652481877907e-06, -0.9995511228404026,
    0.02710907423747958, 4.918077245360215e-06, -0.9996324814802772,
    0.02453182521545951, 4.942730519008739e-06, -0.999699049457173,
    0.02219743470872043, 4.839146287488288e-06, -0.9997536065577425,
    0.020087085569300712, 4.8635685811971475e-06, -0.9997982341071047,
    0.018175168194095488, 4.755231732362265e-06, -0.9998348179526118,
    0.01644728143605838, 4.7792175503368365e-06, -0.9998647342816078,
    0.014881391806977323, 4.6663807824045885e-06, -0.9998892659206828,
    0.013466759312180573, 4.68970834380417e-06, -0.9999093190467658,
    0.012184252187915919, 4.5726248811207615e-06, -0.9999257692050946,
    0.011026167417498943, 4.595062080857636e-06, -0.9999392099279196,
    0.009975720663233217, 4.473988269507734e-06, -0.9999502412196709,
    0.009027730805385407, 4.495297187764624e-06, -0.9999592491656588,
    0.008167306576362112, 4.3704940324797335e-06, -0.999966646952574,
    0.00739136413677462, 4.390434487685896e-06, -0.9999726834508595,
    0.006686533664279679, 4.2621685001914685e-06, -0.9999776448391869,
    0.006051478668305788, 4.280500977739954e-06, -0.9999816895893425,
    0.00547404739264964, 4.149044585476251e-06, -0.9999850172437814,
    0.004954362240960689, 4.165532764885223e-06, -0.9999877270242814,
    0.0044812423124673, 4.031164447748491e-06, -0.9999899591349096,
    0.00405603095537498, 4.045577476405505e-06, -0.9999917742230414,
    0.0036683170730400843, 3.908581744623606e-06, -0.9999932716521832,
    0.003320468444368775, 3.920696355735923e-06, -0.9999944871781636,
    0.0030026806225796785, 3.7813636448464084e-06, -0.999995491892564,
    0.002718183267710608, 3.7909661823294155e-06, -0.9999963056800747,
    0.0024576465225198017, 3.6495927156775934e-06, -0.9999969799287647,
    0.002225027201199395, 3.6564811044774307e-06, -0.9999975245693485,
    0.0020113634774121666, 3.513368755678867e-06, -0.9999979771513966,
    0.001821227374214884, 3.5173544387953966e-06, -0.9999983415079575,
    0.0016459394471832758, 3.3728106135038046e-06, -0.9999986453842098,
    0.0014905936316071222, 3.3737204643172754e-06, -0.9999988890071542,
    0.0013467243573772347, 3.22805801083817e-06, -0.9999990931083804,
    0.0012198694379692808, 3.225736219883606e-06, -0.9999992559000972,
    0.001101722720312085, 3.079273370442352e-06, -0.9999993930440473,
    0.0009982003520988619, 3.073583298363171e-06, -0.9999995017377321,
    0.0009011126552074244, 2.926643636594942e-06, -0.9999995939373797,
    0.0008166987886057432, 2.9174696190960527e-06, -0.9999996664401449,
    0.0007368520431103718, 2.7703820641129857e-06, -0.9999997284628301,
    0.0006680876307882014, 2.7576311499169266e-06, -0.9999997767670211,
    0.0006023560362124552, 2.6107299428981326e-06, -0.9999998185208873,
    0.0005464084131708987, 2.59433354176974e-06, -0.9999998506555365,
    0.0004922329967797593, 2.4479582173061834e-06, -0.999999878789707,
    0.0004467823771297858, 2.4278736320680347e-06, -0.9999999001285206,
    0.00040206828082055333, 2.28236895344209e-06, -0.9999999191061079,
    0.0003652148209197376, 2.2585807674791323e-06, -0.9999999332440969,
    0.000328247198464377, 2.114296602666619e-06, -0.9999999460617496,
    0.0002984349002438084, 2.0868178927539213e-06, -0.9999999554027109,
    0.0002678100530564323, 1.9441090062447713e-06, -0.9999999640731663,
    0.0002437644563554895, 1.9129823496304767e-06, -0.9999999702233426,
    0.00021833344679175965, 1.7722080842121822e-06, -0.9999999760990662,
    0.00019901061228607048, 1.7375063287959348e-06, -0.9999999801308953,
    0.0001778330936959373, 1.5990301512805715e-06, -0.9999999841211616,
    0.0001623778306575413, 1.560856918465771e-06, -0.9999999867499549,
    0.0001446842430231951, 1.4250458039890996e-06, -0.9999999894664735,
    0.0001323959068102969, 1.3835356953870688e-06, -0.9999999911687432,
    0.00011755652220867742, 1.250759326404533e-06, -0.9999999930233623,
    0.00010786100989095783, 1.2060778080348221e-06, -0.9999999941160471,
    9.536058666136381e-05, 1.0767075664718417e-06, -0.9999999953863203,
    8.778740770660859e-05, 1.0290505074176374e-06, -0.9999999960798139,
    7.720443708495184e-05, 9.03458241593564e-07, -0.9999999969530078,
    7.136793952425163e-05, 8.530510882142097e-07, -0.9999999973866367,
    6.235765264030588e-05, 7.316076401077821e-07, -0.999999997989279,
    5.7941651749561024e-05, 6.787042118195558e-07, -0.9999999982550262,
    5.022210565407935e-05, 5.617776949186679e-07, -0.9999999986727508,
    4.6967298619131436e-05, 5.066585931596031e-07, -0.9999999988311101,
    4.030798345893421e-05, 3.9461241645885695e-07, -0.9999999991219923,
    3.8001645200522564e-05, 3.375830446570446e-07, -0.999999999212554,
    3.221415574159782e-05, 2.307736842275228e-07, -0.9999999994160748,
    3.068170254376647e-05, 1.7216188328028037e-07, -0.9999999994645872,
    2.5612100008349653e-05, 7.093640912059025e-08, -0.999999999607664,
    2.471018248767392e-05, 1.108971993169544e-08, -0.9999999996307372,
    2.0232740440109557e-05, -8.421690762290708e-08, -0.9999999997317842,
    1.984358871641929e-05, -1.4493433575371069e-07, -0.9999999997400201,
    1.585567222194288e-05, -2.3400217908207143e-07, -0.9999999998116844,
    1.5882466363178555e-05, -2.9521300812641566e-07, -0.9999999998117529,
    1.2300339078775888e-05, -3.777402471674025e-07, -0.9999999998627606,
    1.2663419006739326e-05, -4.3905766481814543e-07, -0.9999999998587756,
    9.418810065923217e-06, -5.147638395481583e-07, -0.9999999998951792,
    1.0052572774633026e-05, -5.757955282733294e-07, -0.9999999998896067,
    7.089865790151882e-06, -6.444248885019817e-07, -0.9999999999156287,
    7.940225294190417e-06, -7.047772025653927e-07, -0.9999999999098844,
    5.214156745836777e-06, -7.661021190944069e-07, -0.99999999992849,
    6.236464747759006e-06, -8.253844170506934e-07, -0.999999999923329,
    3.710239446711293e-06, -8.792088032613557e-07, -0.9999999999366156,
    4.867583195255348e-06, -9.370378783323201e-07, -0.9999999999323873,
    2.511331240638766e-06, -9.832005670917546e-07, -0.9999999999418492,
    3.773140186093345e-06, -1.0392051136225815e-06, -0.9999999999386608,
    1.5626535241608762e-06, -1.0775831311535387e-06, -0.9999999999453709,
    2.9035587704843383e-06, -1.1314081821481697e-06, -0.9999999999431913,
    8.192566809381979e-07, -1.1619198583008958e-06, -0.9999999999479263,
    2.218157382794248e-06, -1.2132311269500357e-06, -0.9999999999466523,
    2.442393997508726e-07, -1.2358389802347959e-06, -0.9999999999499781,
    1.6835385632111264e-06, -1.2843270374500719e-06, -0.9999999999494741,
    -1.927091418657835e-07, -1.299040373297824e-06, -0.999999999951806,
    1.2722698093554776e-06, -1.344424593608524e-06, -0.9999999999519283,
    -5.165027787754796e-07, -1.3513017556642968e-06, -0.9999999999535725,
    9.6180358054605e-07, -1.3933339654415305e-06, -0.9999999999541833,
    -7.476354787442673e-07, -1.3924841822711592e-06, -0.9999999999553658,
    7.335930840653454e-07, -1.4309519471204593e-06, -0.9999999999563398,
    -9.029813234874137e-07, -1.4225367205112932e-06, -0.9999999999572284,
    5.723683396307473e-07, -1.4572662127895785e-06, -0.999999999958456,
    -9.964494725122504e-07, -1.4415001988079944e-06, -0.9999999999591742,
    4.655434603227392e-07, -1.472358591520112e-06, -0.9999999999605627,
    -1.0395204025136796e-06, -1.4495099315842255e-06, -0.9999999999612007,
    4.027313633128239e-07, -1.4764072713191213e-06, -0.9999999999626732,
    -1.0416849416944535e-06, -1.4467973376620827e-06, -0.9999999999632962,
    3.7534644300788815e-07, -1.4696878566349627e-06, -0.9999999999647904,
    -1.010803710060438e-06, -1.433690384557234e-06, -0.9999999999654439,
    3.7627927556477573e-07, -1.4525732201064792e-06, -0.9999999999669106,
    -9.534013770375093e-07, -1.4106128082091396e-06, -0.9999999999676253,
    3.9963031869774734e-07, -1.4255321071121512e-06, -0.9999999999690273,
    -8.74907528558087e-07, -1.378082076114935e-06, -0.9999999999698217,
    4.404919402460155e-07, -1.3891264706747435e-06, -0.9999999999711308,
    -7.798537921448797e-07, -1.3367060812859903e-06, -0.9999999999720143,
    4.94770048051174e-07, -1.344007534129695e-06, -0.9999999999732112,
    -6.720351145215281e-07, -1.2871785745737087e-06, -0.9999999999741865,
    5.590381801145076e-07, -1.290910599311729e-06, -0.9999999999752586,
    -5.546416514879243e-07, -1.2302733633475956e-06, -0.9999999999763224,
    6.304182115089749e-07, -1.2306486384853598e-06, -0.9999999999772627,
    -4.30366556499866e-07, -1.1668373248849521e-06, -0.9999999999784074,
    7.064828953577031e-07, -1.1641047284673818e-06, -0.9999999999792145,
    -3.014939952828045e-07, -1.0977823027711967e-06, -0.9999999999804295,
    7.851763221941588e-07, -1.0922234049912044e-06, -0.9999999999811048,
    -1.6997093009839454e-07, -1.0240759737485216e-06, -0.9999999999823769,
    8.64749090321337e-07, -1.016001033984366e-06, -0.9999999999829255,
    -3.746557715320519e-08, -9.467317904347486e-07, -0.9999999999842397,
    9.437055582038902e-07, -9.364753137288731e-07, -0.9999999999846693,
    9.458508201752695e-08, -8.667981218328958e-07, -0.9999999999860099,
    1.0207610221177893e-06, -8.547140375299155e-07, -0.9999999999863297,
    2.2493678097215223e-07, -7.853467282602243e-07, -0.99999999998768,
    1.0948070476583633e-06, -7.718032602430842e-07, -0.9999999999879009,
    3.5250683453983456e-07, -7.034607199707579e-07, -0.9999999999892443,
    1.1648834982241204e-06, -6.888350235487166e-07, -0.9999999999893783,
    4.7634906887812727e-07, -6.222221590932091e-07, -0.999999999990698,
    1.2301560603440522e-06, -6.068948040006271e-07, -0.9999999999907575,
    5.956337255929828e-07, -5.426994723623215e-07, -0.9999999999920374,
    1.2898982754676061e-06, -5.270488544412082e-07, -0.9999999999920355,
    7.096314397953369e-07, -4.6593484733679666e-07, -0.99999999999326,
    1.3434772594238893e-06, -4.5033161324228283e-07, -0.9999999999932091,
    8.177005473062739e-07, -3.929317872685577e-07, -0.9999999999943637,
    1.390342431444713e-06, -3.777333569186337e-07, -0.9999999999942766,
    9.19277103784566e-07, -3.246429994609048e-07, -0.9999999999953477,
    1.4300166903889972e-06, -3.101882699419986e-07, -0.9999999999952364,
    1.0138671037317864e-06, -2.6195878882167447e-07, -0.9999999999962117,
    1.462089571492904e-06, -2.48563101072309e-07, -0.9999999999960872,
    1.1010404745545777e-06, -2.056961224228414e-07, -0.9999999999969554,
    1.4862119966012781e-06, -1.9364656828801178e-07, -0.9999999999968283,
    1.180426493750803e-06, -1.565885223104215e-07, -0.9999999999975798,
    1.5020922976867335e-06, -1.46139664549219e-07, -0.9999999999974591,
    1.2517103387964511e-06, -1.1527693270120418e-07, -0.9999999999980854,
    1.5094932502067404e-06, -1.0664700432255145e-07, -0.9999999999979792,
    1.3146305318585748e-06, -8.230169423370974e-08, -0.9999999999984736,
    1.5082299016693711e-06, -7.566933623199681e-08, -0.999999999998388,
    1.3689770870192934e-06, -5.809574232506734e-08, -0.9999999999987449,
    1.4981680234568884e-06, -5.359733060958936e-08, -0.999999999998685,
    1.4145902078761539e-06, -4.297912917564897e-08, -0.9999999999989008,
    1.4792230519502213e-06, -4.070673237222626e-08, -0.99999999999887,
    1.451359419507405e-06, -3.715494984171909e-08, -0.999999999998933,
))


# ═════════════════════════════════ auxil.py ═════════════════════════════════
def check_entry_integrity(res: str, min: float, max: float) -> "None | float":
    def check_valid_float(res):
        try:
            a = float(res)
            if a >= min and a <= max:
                return a
            else:
                return None
        except ValueError:
            return None

    if res == "":
        return None
    return check_valid_float(res)


# ═════════════════════════════════ server.py ════════════════════════════════
# global parameters of discretized models
# эту клетку можно использовать, чтобы задать значения
SpinChainParams = {
    "gamma": 1,
    "gilbert_damping": 0.5,  # в тексте коэффициент затухания Гильберта alpha
    "easy_axis_const": 1,  # после обезразмеривания всегда 1
    "hard_axis_const": 1,  # в тексте k1
    "external_z_field": 0.04,  # поле по оси z, обезразмерено
    "exchange_const": 100,  #  в тексте beta
    "no_of_spins": 201,  # длина цепочки N
    "t_span": (0, 20),
}


def h_eff_calc(t, m_curr, m_neighb, system):
    mx, my, mz = m_curr
    mx1, my1, mz1 = m_neighb
    k = system["easy_axis_const"]
    k1 = system["hard_axis_const"]
    h = system["external_z_field"]
    a = system["exchange_const"]
    return [a * mx1, -k1 * my + a * my1, k * mz + a * mz1 + h]


def single_spin_dot(t, h_eff, m, system):
    mx, my, mz = m
    hx, hy, hz = h_eff
    alpha = system["gilbert_damping"]
    gamma_red = system["gamma"] / (1 + alpha * alpha)
    scalar_prod = mx * hx + my * hy + mz * hz
    mx_dot = -gamma_red * (my * hz - mz * hy) - alpha * gamma_red * (
        mx * scalar_prod - hx
    )
    my_dot = -gamma_red * (mz * hx - mx * hz) - alpha * gamma_red * (
        my * scalar_prod - hy
    )
    mz_dot = -gamma_red * (mx * hy - my * hx) - alpha * gamma_red * (
        mz * scalar_prod - hz
    )
    return [mx_dot, my_dot, mz_dot]


def curr_spin_extraction(m, n, k):
    return m[3 * k : 3 * k + 3]


def neighbour_spin(m, n, k):
    if k == 0:
        return m[3:6]
    elif k == n - 1:
        return m[3 * n - 6 : 3 * n - 3]
    else:
        return [
            m[3 * k - 3] + m[3 * k + 3],
            m[3 * k - 2] + m[3 * k + 4],
            m[3 * k - 1] + m[3 * k + 5],
        ]


def init_values_gen_old(n, center):
    k = center
    return [
        1 if (i % 3 == 2 and i < 3 * k) else -1 if (i % 3 == 2) else 0
        for i in range(3 * n)
    ]


def init_values_gen(n, center):
    k = center
    return [0, 0, 1] * (k - 2) + [1, 0, 0] * 5 + [0, 0, -1] * (n - k - 3)


def system_drive(t, m, system, progress):
    n = system["no_of_spins"]
    progress["value"] = (
        float(t - system["t_span"][0])
        / float((system["t_span"][1] - system["t_span"][0]))
        * config.full_progress
    )
    progress.update()
    return [
        elem
        for x in range(n)
        for elem in single_spin_dot(
            t,
            h_eff_calc(
                t, curr_spin_extraction(m, n, x), neighbour_spin(m, n, x), system
            ),
            curr_spin_extraction(m, n, x),
            system,
        )
    ]


def calculate_B(progress):
    # для минимизации энергии нужно задать нечетное N, указать center в центре цепочки, например при N = 201, center = 101
    # выбрать затухание
    SpinChainParams = {
        "gamma": 1,
        "gilbert_damping": config.B['alpha'],  # в тексте коэффициент затухания Гильберта alpha
        "easy_axis_const": 1,  # после обезразмеривания всегда 1
        "hard_axis_const": 1,  # в тексте k1
        "external_z_field": config.B['b'],  # поле по оси z, обезразмерено
        "exchange_const": config.B['beta'],  #  в тексте beta
        "no_of_spins": 201,  # длина цепочки N
        "t_span": (0, config.B['T']),
    }

    n = SpinChainParams["no_of_spins"]
    center = 101
    init_cond = init_values_gen(n, center)
    t_span = SpinChainParams['t_span']
    t_eval = np.linspace(
        *t_span, 200
    )  # последний параметр - число точек на графике, можно его немного уменьшить, если хочется ускорить вычисление
    
    solution = solve_ivp(
        fun=system_drive,
        t_span=t_span,
        y0=init_cond,
        args=(SpinChainParams, progress),
        t_eval=t_eval,
    )
    config.solution_B = [{'y': solution.y, 't':solution.t}, deepcopy(config.B)]

def calculate_C(progress):
    # для минимизации энергии нужно задать нечетное N, указать center в центре цепочки, например при N = 201, center = 101
    # выбрать затухание
    config.C['L'] = int(config.C['L'])
    
    SpinChainParams = {
        "gamma": 1,
        "gilbert_damping": config.C['alpha'],  # в тексте коэффициент затухания Гильберта alpha
        "easy_axis_const": 1,  # после обезразмеривания всегда 1
        "hard_axis_const": 1,  # в тексте k1
        "external_z_field": config.C['b'],  # поле по оси z, обезразмерено
        "exchange_const": config.C['beta'],  #  в тексте beta
        "no_of_spins": config.C['L']+50,  # длина цепочки N
        "t_span": (0, config.C['T']),
    }
    
    init_cond = init[:(50+config.C['L'])*3]
    t_span = SpinChainParams['t_span']
    t_eval = np.linspace(
        *t_span, 200
    )  # последний параметр - число точек на графике, можно его немного уменьшить, если хочется ускорить вычисление
    solution = solve_ivp(
        fun=system_drive,
        t_span=t_span,
        y0=init_cond,
        args=(SpinChainParams, progress),
        t_eval=t_eval,
    )
    config.solution_C = [{'y': solution.y, 't':solution.t}, deepcopy(config.C)]


# ═════════════════════════════════ files.py ═════════════════════════════════
def save(parent):
    filename = filedialog.asksaveasfilename(
        defaultextension=".ispho", title=MSG["save"], parent=parent
    )
    if filename == "":
        return
    filename = filename[:-6] + ".ispho"

    try:
        f = open(filename, "w")
        f.close()

        if config.task == "B":
            pardict = config.B
            pardict.update({"task": "B"})
            parstr = json.dumps(pardict)
            sol = config.solution_B[0]
            np.vstack((sol["t"], sol["y"])).tofile(filename, sep=";")
        else:
            pardict = config.C
            pardict.update({"task": "C"})
            parstr = json.dumps(pardict)
            sol = config.solution_C[0]
            np.vstack((sol["t"], sol["y"])).tofile(filename, sep=";")

        with open(filename, "a") as f:
            f.write("\n" + parstr)

    except PermissionError:
        messagebox.showwarning(*MSG["perm"])


def open_file(parent):
    filename = filedialog.askopenfilename(
        defaultextension=".ispho", title=MSG["open"], parent=parent
    )
    if filename == "":
        return False
    with open(filename, "r") as f:
        s = f.read()
    s = s.split("\n")
    arr = np.fromstring(s[0], sep=";").reshape(-1, 200)
    params = json.loads(s[1])
    task = params.pop("task")
    if task == "B":
        config.task = "B"
        config.solution_B = [{"t": arr[0, :], "y": arr[1:, :]}, params]
        config.B = config.solution_B[1]

    else:
        config.task = "C"
        config.solution_C = [{"t": arr[0, :], "y": arr[1:, :]}, params]
        config.C = config.solution_C[1]

    return True


# ═════════════════════════════════ plots.py ═════════════════════════════════
# plotting is derived from https://matplotlib.org/examples/user_interfaces/embedding_in_tk.html

# MPL and stuff
# import matplotlib

# matplotlib.use("TkAgg")


class buildplot(tk.Frame):
    def __init__(self, master):
        # create canvas
        super().__init__(master)
        self.figure = Figure(figsize=(10, 6), dpi=100, tight_layout=True)
        self.ax = self.figure.add_subplot(111)
        # self.is_drawen = 0
        self.master = master

        # PLOT CANVAS
        self.canvas = FigureCanvasTkAgg(self.figure, master=master)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, columnspan=2)

        # NAV TOOLBAR
        toolbarFrame = tk.Frame(master=master)
        toolbarFrame.grid(row=1, columnspan=2, sticky="ew")
        NavigationToolbar2Tk(self.canvas, toolbarFrame)

    def update_plot(self):
        # Setting up axes labels and threshold
        self.ax.clear()

        if config.task == "B":
            if config.solution_B is not None:
                sol = config.solution_B[0]
                params = config.solution_B[1]
                true_time = sol["t"][np.argmin(np.abs(config.t - sol["t"]))]
                tt_solution = sol["y"][:, np.argmin(np.abs(config.t - sol["t"]))]
                mx = tt_solution[0::3]
                my = tt_solution[1::3]
                mz = tt_solution[2::3]

                self.ax.plot(mx, label=r"$m_x$")
                self.ax.plot(my, label=r"$m_y$")
                self.ax.plot(mz, label=r"$m_z$")
                self.ax.set_title(
                    f"[B] | Time: {true_time:.2f} / {params['T']:.2f} | $\\alpha$: {params['alpha']:.2f} |  $\\beta$: {params['beta']:.2f} | $b$: {params['b']:.2f}"
                )

        else:
            if config.solution_C is not None:
                sol = config.solution_C[0]
                params = config.solution_C[1]
                true_time = sol["t"][np.argmin(np.abs(config.t - sol["t"]))]
                tt_solution = sol["y"][:, np.argmin(np.abs(config.t - sol["t"]))]
                mx = tt_solution[0::3]
                my = tt_solution[1::3]
                mz = tt_solution[2::3]

                self.ax.plot(mx, label=r"$m_x$")
                self.ax.plot(my, label=r"$m_y$")
                self.ax.plot(mz, label=r"$m_z$")
                self.ax.set_title(
                    f"[C] | Time: {true_time:.2f} / {params['T']:.2f} | $\\alpha$: {params['alpha']:.2f} |  $\\beta$: {params['beta']:.2f} | $b$: {params['b']:.2f} | $L$: {params['L']:.2f}"
                )

        # Main grid
        self.ax.grid(
            True, which="major", linestyle="-", linewidth=1.0, alpha=0.8, color="gray"
        )

        # Minor grid
        self.ax.grid(
            True, which="minor", linestyle="--", linewidth=0.5, alpha=0.5, color="gray"
        )
        self.ax.minorticks_on()

        if not self.ax.get_legend_handles_labels() == ([], []):
            self.ax.legend()

        # Unknown error, neglecting
        try:
            self.canvas.draw()
        except AttributeError as e:
            stderr.write(str(e))


# ═════════════════════════════════ panel.py ═════════════════════════════════
# python imports

# import CCDfiles
# import CCDserial
# from CCDhelp import *


class Panel(tk.Frame):
    def __init__(self, master, plot):
        tk.Frame.__init__(self, master=master)
        self.__row_counter = 0

        plot.master = self
        self.plot_field = plot

        # Create all widgets and space between them
        self.collect_selector_panel()

        self.insert_vskip(20)

        self.collect_parameter_panel("alpha", "α", 0, 1)
        self.insert_vskip(10)
        self.collect_parameter_panel("beta", "β", 0, 500)
        self.insert_vskip(10)
        self.collect_parameter_panel("b", "b", 0, 1)
        self.insert_vskip(10)
        self.collect_parameter_panel("T", "T", 0, 100)
        self.insert_vskip(10)
        self.collect_parameter_panel("L", "L", 50, 200)

        self.insert_vskip(40)

        self.collect_calculate_panel()

        self.insert_vskip(40)

        self.collect_plot_panel()

        self.insert_vskip(40)
        self.collect_files_panel()

        self.UIconfigure_init()

        self.updateplot()

    def insert_vskip(self, size):
        self.grid_rowconfigure(
            self.__row_counter,
            minsize=size,
        )
        self.__row_counter += 1

    def getobj(self, name: str) -> Widget:
        return self.nametowidget(name)

    def collect_selector_panel(self):
        self.variable_task = tk.StringVar(master=self, value="B", name="variable_task")

        label_address = tk.Label(self, text="Select task:", name="label_task")
        label_address.grid(column=0, row=self.__row_counter)

        def callback(var, index, mode):
            try:
                if self.variable_task.get() == "C":
                    config.task = "C"
                    self.UIconfigure_switch_to_C()
                else:
                    config.task = "B"
                    self.UIconfigure_switch_to_B()
            except KeyError as e:
                print(e.__str__())

        self.variable_task.trace_add(mode="write", callback=callback)

        combobox_task = ttk.Combobox(
            self,
            values=config.tasks,
            state="readonly",
            textvariable=self.variable_task,
            name="combobox_task",
            justify="center",
            width=10,
        )

        combobox_task.set(config.task)
        self.variable_task.set(config.task)
        combobox_task.grid(column=1, row=self.__row_counter)

        self.__row_counter += 1

    def collect_parameter_panel(
        self, par_name: str, descr: str, min: float, max: float
    ):
        variable = tk.StringVar(master=self, value="", name="variable_" + par_name)

        def callback(name, index, mode, value):
            result = check_entry_integrity(value.get(), min, max)
            if result is not None:
                if config.task == "B":
                    config.B[par_name] = result
                else:
                    config.C[par_name] = result
                self.getobj("entry_" + par_name)["background"] = "#AAFFAA"
            else:
                if config.task == "B":
                    config.B[par_name] = None
                else:
                    config.C[par_name] = None
                self.getobj("entry_" + par_name)["background"] = "#FFAAAA"
                self.getobj("button_calculate")["state"] = tk.DISABLED

            if config.task == "B":
                if None not in config.B.values():
                    self.getobj("button_calculate")["state"] = tk.NORMAL
            if config.task == "C":
                if None not in config.C.values():
                    self.getobj("button_calculate")["state"] = tk.NORMAL

        variable.trace_add(
            mode="write",
            callback=lambda name, index, mode, value=variable: callback(
                name, index, mode, value
            ),
        )

        label = tk.Label(self, text=descr, name="label_" + par_name)
        entry = tk.Entry(
            self,
            state="normal",
            textvariable=variable,
            justify="right",
            name="entry_" + par_name,
        )

        def on_focus_out(event):
            if config.task == "B":
                if config.B[par_name] is not None:
                    self.getobj("entry_" + par_name)["background"] = "#DDFFDD"
            else:
                if config.C[par_name] is not None:
                    self.getobj("entry_" + par_name)["background"] = "#DDFFDD"

        entry.bind("<FocusOut>", on_focus_out)

        label.grid(column=0, row=self.__row_counter)
        entry.grid(column=1, row=self.__row_counter)

        self.__row_counter += 1

    def collect_calculate_panel(self):
        def button_calculate_callback():
            self.UIconfigure_calc_started()
            if config.task == "B":
                calculate_B(self.getobj("progressbar"))
            else:
                calculate_C(self.getobj("progressbar"))
            self.UIconfigure_calc_finished()

        button_calculate = tk.Button(
            master=self,
            state="disabled",
            text="Solve",
            justify="center",
            command=button_calculate_callback,
            background="#AAFFAA",
            name="button_calculate",
        )
        button_calculate.grid(
            row=self.__row_counter, column=0, columnspan=2, sticky="EW"
        )
        self.__row_counter += 1

        self.insert_vskip(5)

        progressbar = ttk.Progressbar(
            master=self,
            mode="determinate",
            name="progressbar",
            orient="horizontal",
            maximum=config.full_progress,
        )
        progressbar.update()
        progressbar.grid(row=self.__row_counter, column=0, columnspan=2, sticky="EW")
        self.__row_counter += 1

    def collect_plot_panel(self):
        variable_t = tk.StringVar(master=self, value="", name="variable_t")

        def callback(name, index, mode, value):
            if config.task == "B":
                tmax = config.solution_B[1]["T"]
            else:
                tmax = config.solution_C[1]["T"]
            result = check_entry_integrity(value.get(), 0, tmax)
            if result is not None:
                self.getobj("entry_t")["background"] = "#AAFFAA"
                self.getobj("button_plot")["state"] = tk.NORMAL
                config.t = result
            else:
                self.getobj("entry_t")["background"] = "#FFAAAA"
                self.getobj("button_plot")["state"] = tk.DISABLED
                config.t = None

        variable_t.trace_add(
            mode="write",
            callback=lambda name, index, mode, value=variable_t: callback(
                name, index, mode, value
            ),
        )

        label_t = tk.Label(master=self, text="t:", name="label_t")

        entry_t = tk.Entry(
            master=self,
            text="",
            name="entry_t",
            state="disabled",
            textvariable=variable_t,
        )

        def button_plot_callback():
            self.updateplot()

        button_plot = tk.Button(
            master=self,
            text="Plot",
            state="disabled",
            command=button_plot_callback,
            name="button_plot",
        )

        label_t.grid(row=self.__row_counter, column=0)
        entry_t.grid(row=self.__row_counter, column=1)
        self.__row_counter += 1
        self.insert_vskip(5)
        button_plot.grid(row=self.__row_counter, column=0, columnspan=2, sticky="EW")
        self.__row_counter += 1

    def collect_files_panel(self):
        def button_save_callback():
            save(self)

        button_save = tk.Button(
            name="button_save",
            text="Save",
            justify="center",
            command=button_save_callback,
            master=self,
            state=tk.DISABLED,
        )
        button_save.grid(row=self.__row_counter, column=0, columnspan=2, sticky="ew")
        self.__row_counter += 1

        self.insert_vskip(5)

        def button_open_callback():
            # self.UIconfigure_init()
            if open_file(self):
                self.UIconfigure_file_opened()

        button_open = tk.Button(
            name="button_open",
            text="Load",
            justify="center",
            command=button_open_callback,
            master=self,
            state=tk.NORMAL,
        )
        button_open.grid(row=self.__row_counter, column=0, columnspan=2, sticky="ew")
        self.__row_counter += 1

    def updateplot(self):
        self.plot_field.update_plot()

    # ________________________________________________________
    # Default UI configurators

    def UIconfigure_widgets(self, description):
        """
        A method to easily configure widgets. Preferred to be used with default configurators.

        Args:
            description (dict): a nested dictionary representing the following structure:\n
            (which quality to change) - (to which value) - (what object)
        """

        for quality in description:
            for value in description[quality]:
                for element in description[quality][value]:
                    self.getobj(element)[quality] = (
                        value  # DON'T GET CAUGHT! IT'S A SPECIAL MPL SYNTAX RATHER THAN ELEMENT INDEXING!
                    )

    def UIconfigure_init(self):
        self.UIconfigure_widgets(
            {
                "state": {
                    tk.NORMAL: ["entry_alpha", "entry_beta", "entry_T", "entry_b"],
                    tk.DISABLED: ["entry_L", "button_calculate"],
                    "readonly": ["combobox_task"],
                },
                "background": {
                    "#55FF55": ["button_calculate"],
                    "#FFFFFF": [
                        "entry_alpha",
                        "entry_beta",
                        "entry_T",
                        "entry_b",
                        "entry_L",
                    ],
                },
            }
        )

    def UIconfigure_calc_started(self):
        self.getobj("button_calculate")["background"] = ("#FFAAAA",)
        self.UIconfigure_widgets(
            {
                "state": {
                    tk.DISABLED: [
                        "button_calculate",
                        "entry_alpha",
                        "entry_beta",
                        "entry_L",
                        "entry_T",
                        "entry_b",
                        "button_plot",
                        "entry_t",
                    ]
                }
            }
        )

    def UIconfigure_calc_finished(self):
        self.getobj("progressbar")["value"] = 0
        self.getobj("button_calculate")["background"] = ("#AAFFAA",)
        self.UIconfigure_widgets(
            {
                "state": {
                    tk.NORMAL: [
                        "button_calculate",
                        "entry_t",
                        "entry_alpha",
                        "entry_beta",
                        "entry_T",
                        "entry_b",
                        "button_save",
                    ]
                }
            }
        )
        if config.t is not None:
            self.getobj("button_plot")["state"] = tk.NORMAL
        if config.task == "C":
            self.getobj("entry_L")["state"] = tk.NORMAL

    def UIconfigure_file_opened(self):
        if config.task == "B":
            self.UIconfigure_widgets(
                {
                    "state": {
                        "normal": {
                            "entry_alpha",
                            "entry_beta",
                            "entry_T",
                            "entry_b",
                            "entry_t",
                        },
                        "disabled": {"entry_L", "button_plot"},
                    },
                    "background": {
                        "#FFFFFF": [
                            "entry_alpha",
                            "entry_beta",
                            "entry_T",
                            "entry_b",
                            "entry_L",
                        ]
                    },
                }
            )
            self.setvar("variable_task", config.task)
            self.setvar("variable_beta", config.B["beta"])
            self.setvar("variable_T", config.B["T"])
            self.setvar("variable_b", config.B["b"])
            self.setvar("variable_alpha", config.B["alpha"])

        else:
            self.UIconfigure_widgets(
                {
                    "state": {
                        "normal": {
                            "entry_alpha",
                            "entry_beta",
                            "entry_T",
                            "entry_b",
                            "entry_L",
                            "entry_t",
                        },
                        "disabled": {"button_plot"},
                    },
                    "background": {
                        "#FFFFFF": [
                            "entry_alpha",
                            "entry_beta",
                            "entry_T",
                            "entry_b",
                            "entry_L",
                        ]
                    },
                }
            )

            self.setvar("variable_task", config.task)
            self.setvar("variable_beta", config.C["beta"])
            self.setvar("variable_T", config.C["T"])
            self.setvar("variable_b", config.C["b"])
            self.setvar("variable_alpha", config.C["alpha"])
            self.setvar("entry_L", config.C["L"])

    def UIconfigure_switch_to_C(self):
        self.UIconfigure_init()
        config.task = "C"
        # config.C = {
        #     "alpha": None,
        #     "beta": None,
        #     "b": None,
        #     "T": None,
        #     "L": None,
        # }

        self.getobj("entry_L")["state"] = tk.NORMAL
        self.UIconfigure_widgets(
            {
                "state": {
                    tk.NORMAL: ["entry_L"],
                    tk.DISABLED: ["button_plot", "button_save", "button_calculate"],
                }
            }
        )

        self.setvar("variable_task", config.task)
        # self.setvar("variable_alpha", config.C["alpha"])
        # self.setvar("variable_beta", config.C["beta"])
        # self.setvar("variable_T", config.C["T"])
        # self.setvar("variable_b", config.C["b"])
        # self.setvar("variable_L", config.C['L'])
        self.getobj("entry_alpha").update()

    def UIconfigure_switch_to_B(self):
        self.UIconfigure_init()
        config.task = "B"
        config.B = {"alpha": None, "beta": None, "b": None, "T": None}
        self.UIconfigure_widgets(
            {
                "state": {
                    tk.DISABLED: [
                        "entry_L",
                        "button_plot",
                        "button_save",
                        "button_calculate",
                    ],
                }
            }
        )

        self.variable_task.set(str(config.task))
        self.setvar("variable_alpha", str(config.B["alpha"]))
        self.setvar("variable_task", config.task)
        self.setvar("variable_alpha", config.B["alpha"])
        self.setvar("variable_beta", config.B["beta"])
        self.setvar("variable_T", config.B["T"])
        self.setvar("variable_b", config.B["b"])
        self.setvar("variable_L", config.B["L"])

        self.getobj("entry_alpha")["text"] = "ayapuroa"

        self.getobj("entry_L")["text"] = tk.DISABLED


# ═════════════════════════════════ app.py ═══════════════════════════════════


def init():
    root = tk.Tk()
    root.title("Ferromagnetic Simulator")

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    initGUI(root)
    root.mainloop()


def initGUI(root):
    plot = buildplot(root)
    p = Panel(root, plot)
    p.grid(row=0, column=2, padx=10)


if __name__ == "__main__":
    init()
