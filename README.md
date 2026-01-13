Energy Management System (EMS) - Main script

Copyright (C) 2020-2024 LEAP scarl

Authors:
- Matteo Zatti
- Marco Gabba
- Filippo Bovera

This file is part of EMS

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

# EMS

Energy Management System (EMS) developed by LEAP scarl (www.leap.polimi.it) and Politecnico di Milano (www.polimi.it)

EMS is built using Python language and Pyomo library, exploiting the "Abstract Model" and "Block" functionalities to model energy units, relevant processes and market dynamics in a rigorous yet customizable way.

The main goal of EMS is to plan the management strategy of the energy production and storage systems and of the programmable processes to attain the minimum cost (or other utility function of interest).

It can solve two kind of problems:

## SCHEDULING - Day-ahead scheduling: the plan for tomorrow

The "scheduling" mode solves the problem of finding the best management plan of the energy production, storage and utilization systems for the next calendar day and the exchange program with the power grid (hence, possibly, the participation to the energy markets).

The Mixed-Integer Linear Programming (MILP) at its core allows to model the energy units, the relevant processes and the market dynamics in a rigorous yet customizable way, allowing the creation of a digital twin of the plant.

The goal is, typically, to meet the energy demand at minimal cost, while respecting technical and regulatory constraints, but can be tailored to meet the Facility Manager needs, as, for example, operate minimizing the withdrawn from the grid or the risk of failing the provision of pre-determined services.

The output schedule can be used for the Day-Ahead Market bidding, but there are options to optimize the plant considering also the participation in the Ancillary Services Market (ASM).

## RESCHEDULING - Intra-day scheduling adjustments: reacting to the unexpected
The "rescheduling" mode oversees the re-assessment of the optimal schedule, as events unfold along the current day: forecasts may result erroneous, user choices may change, a market or a system operator signal materialize, a unit may have become unavailable. 

Similarly to the day-ahead model, the near real-time operation module has a MILP at its core. While the former typically uses detailed formulations to ensure accurate results, the latter can be based on simplified or reduced formulations to guarantee the computational tractability or because sub-problems need to be addressed.

This module allows to manage several electricity markets: from buying/selling energy in Intra-Day markets (for example, to compensate for an error in the PV production forecast) to reacting to ASM signals.

# How to use EMS

## preparing the test

The folder "/examples" contains an example of a scheduling problem and a rescheduling problem.
Users can edit default parameter values using the .yaml file (for an extended list of available parameters, check relevant models in the /src folder).

## running the model

The file "Main.py" contains the code to run a test file and display values of relevant variables.
It includes:
- routines for reading the input (either from .yaml files or an already consolidated .txt file containing the overall python dictionary describing input;
- Pyomo instance creation
- Running the problem (Gurobi solver is needed to run the examples)
- Examples of how to print the value of selected variables

Results are serialized in a pickle file using cloudpickle library. This allows the user to access results without having to run the problem again (see report creaction section)

## report creation

The file "Report.py" includes routines to generate comprehensive reports and figures reading the serialized solution of a test.
As an example, routines to save variables and display graphs regarding electric, thermal and natural gas balances are included in the "/src/CIRCUIT.py" file.