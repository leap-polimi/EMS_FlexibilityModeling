# -*- coding: utf-8 -*-
"""
PDR model
"""

from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block
import pyomo.environ as pyo

def create_block(b,g):
    #SETS
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    
    #.. section:: TIME-INDEPENDENT PARAMETERS
    b.cost_naturalGas_p= Param(within=NonNegativeReals) #:param cost_naturalGas_p: cost of natural gas per unit of standard cubic meter [€/Smc]
    b.LHV_p = Param(within=NonNegativeReals) #:param LHV_p: lower heating value of natural gas [kWh/Smc]
    b.cost_networksObligations_p = Param(within=NonNegativeReals) #:param cost_networksObligations_p: cost of network obligation per unit of standard cubic meter [€/Smc]
    b.VAT_p = Param(within=NonNegativeReals) #:param VAT_p: VAT rate [p.u.]
    b.cost_exciseNG_p = Param(within=NonNegativeReals) #:param cost_exciseNG_p: [€/Smc] excise for NG not used to produce electricity
    b.cost_exciseEE_p = Param(within=NonNegativeReals) #:param cost_exciseEE_p: [€/Smc] excise for NG used to produce electricity      
    
    # TIME-DEPENDENT PARAMETERS
    
    #.. section:: VARS
    b.smc_withdrawn_v = Var(b.TIME_s, within=NonNegativeReals) #:param smc_withdrawn_v: standard cubic meters withdrawn [Smc]  
    b.cost_total_v = Var(within=NonNegativeReals) #:param cost_total_v: [€] Total gas expenditures during the optimization window
    b.smc_ElectricityProduction_v = Var(b.TIME_s,within=NonNegativeReals) #:param smc_ElectricityProduction_v: [kWh_el] Electricity Production of units connected to the circuit  (TO BE CONSTRAINED OUTSIDE)    
    b.smc_OtherUses_v = Var(b.TIME_s, within=NonNegativeReals) #:param smc_OtherUses_v: [Smc] HELPER VARIABLE: calculate the fraction of NG consumption subject to NG excise
    
    #CONSTRAINTS
    
    @b.Constraint(b.TIME_s)
    def noCogen_calc(b,t):
        return b.smc_OtherUses_v[t] == b.smc_withdrawn_v[t] - b.smc_ElectricityProduction_v[t]
    
    @b.Constraint()
    def bill_calc(b):
        #Expenditures = (N_O + price)*total withdrawn natural gas +
        #               natural gas not used for electricity production with applied NG excise +
        #               natural gas used for elextricity production with applied EE excise
        #               + VAT
        value = ((b.cost_networksObligations_p + b.cost_naturalGas_p)*sum(b.smc_withdrawn_v[t] for t in b.TIME_s) +\
                sum(b.smc_OtherUses_v[t] for t in b.TIME_s)*b.cost_exciseNG_p +\
                sum(b.smc_ElectricityProduction_v[t] for t in b.TIME_s)*b.cost_exciseEE_p)\
                *(1+b.VAT_p) 
        return b.cost_total_v == value