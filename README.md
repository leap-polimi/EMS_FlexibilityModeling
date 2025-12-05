# EMS

Energy Management System (EMS) developed by LEAP scarl (www.leap.polimi.it) and Politecnico di Milano (www.polimi.it)

EMS is built using Python language and Pyomo library, exploiting the "Abstract Model" and "Block" functionalities to model energy units, relevant processes and market dynamics in a rigorous yet customizable way.

The main goal of EMS is to plan the management strategy of the energy production and storage systems and of the programmable processes to attain the minimum cost (or other utility function of interest).

It can solve two kind of problems:

**SCHEDULING - Day-ahead scheduling: the plan for tomorrow**

The "scheduling" mode solves the problem of finding the best management plan of the energy production, storage and utilization systems for the next calendar day and the exchange program with the power grid (hence, possibly, the participation to the energy markets).

The Mixed-Integer Linear Programming (MILP) at its core allows to model the energy units, the relevant processes and the market dynamics in a rigorous yet customizable way, allowing the creation of a digital twin of the plant.

The goal is, typically, to meet the energy demand at minimal cost, while respecting technical and regulatory constraints, but can be tailored to meet the Facility Manager needs, as, for example, operate minimizing the withdrawn from the grid or the risk of failing the provision of pre-determined services.

The output schedule can be used for the Day-Ahead Market bidding, but there are options to optimize the plant considering also the participation in the Ancillary Services Market (ASM).

**RESCHEDULING - Intra-day scheduling adjustments: reacting to the unexpected**
The "rescheduling" mode oversees the re-assessment of the optimal schedule, as events unfold along the current day: forecasts may result erroneous, user choices may change, a market or a system operator signal materialize, a unit may have become unavailable. 

Similarly to the day-ahead model, the near real-time operation module has a MILP at its core. While the former typically uses detailed formulations to ensure accurate results, the latter can be based on simplified or reduced formulations to guarantee the computational tractability or because sub-problems need to be addressed.

This module allows to manage several electricity markets: from buying/selling energy in Intra-Day markets (for example, to compensate for an error in the PV production forecast) to reacting to ASM signals.