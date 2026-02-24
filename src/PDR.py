# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - PDR (Natural Gas delivery point) block
Copyright (C) 2020-2024 LEAP scarl
Authors:
- Matteo Zatti
- Marco Gabba
- Filippo Bovera

Further development / modifications (fork):
Copyright (C) 2024-2026 Andrea Scrocca and Filippo Bovera
Affiliation: Politecnico di Milano, Department of Energy

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
"""

from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block
import pyomo.environ as pyo

def create_block(b,g):
    #SETS
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    
    #.. section:: TIME-INDEPENDENT PARAMETERS
    b.cost_naturalGas_p= Param(within=NonNegativeReals) #:param cost_naturalGas_p: cost of natural gas per unit of standard cubic meter [€/Smc]
    b.LHV_p = Param(within=NonNegativeReals) #:param LHV_p: lower heating value of natural gas [kWh/Smc]
    b.cost_networksObligations_smc_p = Param(within=NonNegativeReals) #:param cost_networksObligations_smc_p: cost of network obligation per unit of standard cubic meter [€/Smc]
    b.cost_networksObligations_fixed_p = Param(within=NonNegativeReals) #:param cost_networksObligations_fixed_p: cost of network obligation per day [€/day] (original obligation is per month)
    b.VAT_p = Param(within=NonNegativeReals) #:param VAT_p: VAT rate [p.u.]
    b.cost_exciseNG_p = Param(within=NonNegativeReals) #:param cost_exciseNG_p: [€/Smc] excise for NG not used to produce electricity
    b.cost_exciseEE_p = Param(within=NonNegativeReals) #:param cost_exciseEE_p: [€/Smc] excise for NG used to produce electricity      
    
    # TIME-DEPENDENT PARAMETERS
    
    #.. section:: VARS
    b.smc_withdrawn_v = Var(b.TIME_s, within=NonNegativeReals) #:param smc_withdrawn_v: standard cubic meters withdrawn [Smc]  
    b.cost_total_v = Var(within=NonNegativeReals) #:param cost_total_v: [€] Total gas expenditures during the optimization window
    b.smc_ElectricityProduction_v = Var(b.TIME_s,within=NonNegativeReals) #:param smc_ElectricityProduction_v: [kWh_el] Electricity Production of units connected to the circuit  (TO BE CONSTRAINED OUTSIDE)    
    b.smc_OtherUses_v = Var(b.TIME_s, within=NonNegativeReals) #:param smc_OtherUses_v: [Smc] HELPER VARIABLE: calculate the fraction of NG consumption subject to NG excise
    
    b.cost_gas_smc_v = Var(b.TIME_s, within=NonNegativeReals) #:var cost_gas_smc_v: [€] Expenditures for gas price variable component
    b.cost_gas_excise_v = Var(b.TIME_s, within=NonNegativeReals) #:var cost_gas_excise_v: [€] Expenditures for gas excise

    #CONSTRAINTS
    
    @b.Constraint(b.TIME_s)
    def noCogen_calc(b,t):
        return b.smc_OtherUses_v[t] == b.smc_withdrawn_v[t] - b.smc_ElectricityProduction_v[t]
    
    @b.Constraint(b.TIME_s)
    def cost_gas_smc_calc(b,t):
        return b.cost_gas_smc_v[t] == (b.cost_naturalGas_p + b.cost_networksObligations_smc_p)*b.smc_withdrawn_v[t]
    
    @b.Constraint(b.TIME_s)
    def cost_gas_excise_calc(b,t): 
        return b.cost_gas_excise_v[t] == b.cost_exciseNG_p*b.smc_OtherUses_v[t] + b.cost_exciseEE_p*b.smc_ElectricityProduction_v[t]
    
    @b.Constraint()
    def bill_calc(b):
        #Expenditures = (var_N_O + price)*total withdrawn natural gas +
        #               ng excise cost +
        #               fixed_N_O +
        #               + VAT
        value = (sum(b.cost_gas_smc_v[t] for t in b.TIME_s) +\
                sum(b.cost_gas_excise_v[t] for t in b.TIME_s) +\
                b.cost_networksObligations_fixed_p )\
                *(1+b.VAT_p) 
        return b.cost_total_v == value