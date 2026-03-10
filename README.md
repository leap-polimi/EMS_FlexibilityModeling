# EMS4Flex

Energy Management System (EMS) originally developed by [**LEAP scarl**](https://www.leap.polimi.it) and [**Politecnico di Milano**](https://www.polimi.it).

This repository is a **fork of the original EMS project**.
It extends the original modeling framework by introducing detailed flexibility modeling, aimed at assessing both **implicit and explicit flexibility provision by multi-energy systems**.

## Fork authorship and contributions

Modifications in this fork are authored by:
- Andrea Scrocca
- Filippo Bovera

Affiliation: Politecnico di Milano, Department of Energy

The original EMS project is credited to its original authors and maintainers (see “Original project credits” below).

---

## What’s new in this fork

The major development in this fork is the detailed modeling of the flexibility that the system can provide.

### 1) Implicit flexibility via detailed Italian electricity bill structure

This fork introduces a more accurate representation of the Italian electricity bill, enabling the investigation of implicit flexibility provision (i.e., flexibility driven by tariff components and billing structure rather than explicit market remuneration). In particular, it adds novel modeling for negative injected energy for BESS in the Italian context. This allows the BESS to treat previously withdrawn energy as exempt from grid tariffs if it is later re-injected into the grid (i.e., under a pure arbitrage operation).

### 2) Explicit flexibility via enhanced FLEX block

This fork strengthens the FLEX block to model explicit flexibility service provision, enabling participation in a Local Flexibility Market (LFM).

Flexibility services are modeled through two key elements:
- Power reserve (capacity committed for service provision)
- Service activation (energy actually delivered when the service is called)

---

## How to use the model to optimize implicit flexibility provision

The model can capture implicit flexibility from controllable assets, since electricity withdrawals are priced according to the Italian retail bill structure. In particular, the objective accounts for:
- energy-based grid charges [€/kWh],
- capacity-based charges [€/kW],
- fixed charges [€/month].

As a result, the optimizer may shift consumption and production to reduce total bill components even without any explicit flexibility remuneration. If you want to represent a different billing or tariff framework, you may need to adapt the POD parameters and related constraints accordingly.

---

## How to use the model to optimize participation in explicit flexibility schemes

The model can be used in two main modes for explicit flexibility provision, depending on whether you are planning reserve bids ahead of time or operating under real-time dispatch instructions.

### 1) Optimize power-reserve bids in month-ahead or day-ahead auctions (Scheduling)
Use this mode to determine how much upward reserve capacity should be retained from flexible assets (e.g., BESS, CHP) so that the site can comply with possible DSO activation requests during the availability window.

Set:
- logic_schedulingReschedulingSelection_p = 0 (scheduling)
- FLEX_b.logic_is_capacityRetention_Optimized_p == 1 (capacity retention is a variable, i.e. it has to be optimized)

Provide as inputs:
- Reserve remuneration (€/MW/h)
- Activation remuneration (€/MWh)
- Service specifications (availability time window, max duration of activation, etc.)
- Forecasts for uncertain variables (loads, renewable generation, prices, etc.)

Output:
- The economically optimal power band to reserve and offer in the market, ensuring feasibility against potential dispatch orders within the DSO-defined time window.

Note: Since this is a forward-planning stage, results strongly depend on provided forecasts.

### 2) Optimize system operation under real-time measurements and dispatching orders (Rescheduling)
Use this mode when the DSO provides dispatching/activation orders close to real time (e.g., with at least 1 hour notice). The model can then be run in a rolling-horizon mode:
- Optimize control actions for the next hour using measured inputs and considering potential dispatching orders
- Re-optimize the remaining horizon (e.g., the next 23 hours) using updated forecasts

Set:
- logic_schedulingReschedulingSelection_p = 1 (rescheduling)
- logic_rescheduling_localGlobalSelection_p = 0 (local flexibility provision)

Key feature:
- If strict compliance with dispatch orders would make the problem infeasible (e.g., because reserves were over-committed due to forecast errors), the model can allow limited non-compliance by introducing a penalty term

### How flexibility provision is measured: Baseline

In both modes, flexibility provision is measured at the Point of Delivery (POD) with respect to a predefined baseline. The power reserve and service activation are therefore evaluated as deviations of the POD net exchange with respect of the pre-defined baseline.

---

## EMS (Original project description)

Energy Management System (EMS) developed by LEAP scarl (www.leap.polimi.it) and Politecnico di Milano (www.polimi.it)

EMS is built using Python language and Pyomo library, exploiting the "Abstract Model" and "Block" functionalities to model energy units, relevant processes and market dynamics in a rigorous yet customizable way.

The main goal of EMS is to plan the management strategy of the energy production and storage systems and of the programmable processes to attain the minimum cost (or other utility function of interest).

It can solve two kind of problems:

### SCHEDULING - Day-ahead scheduling: the plan for tomorrow

The "scheduling" mode solves the problem of finding the best management plan of the energy production, storage and utilization systems for the next calendar day and the exchange program with the power grid (hence, possibly, the participation to the energy markets).

The Mixed-Integer Linear Programming (MILP) at its core allows to model the energy units, the relevant processes and the market dynamics in a rigorous yet customizable way, allowing the creation of a digital twin of the plant.

The goal is, typically, to meet the energy demand at minimal cost, while respecting technical and regulatory constraints, but can be tailored to meet the Facility Manager needs, as, for example, operate minimizing the withdrawn from the grid or the risk of failing the provision of pre-determined services.

The output schedule can be used for the Day-Ahead Market bidding, but there are options to optimize the plant considering also the participation in the Ancillary Services Market (ASM).

### RESCHEDULING - Intra-day scheduling adjustments: reacting to the unexpected

The "rescheduling" mode oversees the re-assessment of the optimal schedule, as events unfold along the current day: forecasts may result erroneous, user choices may change, a market or a system operator signal materialize, a unit may have become unavailable.

Similarly to the day-ahead model, the near real-time operation module has a MILP at its core. While the former typically uses detailed formulations to ensure accurate results, the latter can be based on simplified or reduced formulations to guarantee the computational tractability or because sub-problems need to be addressed.

This module allows to manage several electricity markets: from buying/selling energy in Intra-Day markets (for example, to compensate for an error in the PV production forecast) to reacting to ASM signals.

---

## How to use EMS

### Preparing the test

The folder /examples contains an example of a scheduling problem and a rescheduling problem.
Users can edit default parameter values using the .yaml file (for an extended list of available parameters, check relevant models in the /src folder).

### Running the model

The file Main.py contains the code to run a test file and display values of relevant variables.
It includes:

routines for reading the input (either from .yaml files or an already consolidated .txt file containing the overall python dictionary describing input);

Pyomo instance creation;

running the problem (Gurobi solver is needed to run the examples);

examples of how to print the value of selected variables.

Results are serialized in a pickle file using cloudpickle library. This allows the user to access results without having to run the problem again (see report creation section).

### Report creation

The file Report.py includes routines to generate comprehensive reports and figures reading the serialized solution of a test.
As an example, routines to save variables and display graphs regarding electric, thermal and natural gas balances are included in the /src/CIRCUIT.py file.

---

## Original project credits

Energy Management System (EMS) - Main script
Copyright (C) 2020-2024 LEAP scarl

Authors:
- Matteo Zatti
- Marco Gabba
- Filippo Bovera

This file is part of EMS

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see https://www.gnu.org/licenses/.