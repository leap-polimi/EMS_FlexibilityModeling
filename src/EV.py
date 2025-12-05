# -*- coding: utf-8 -*-
"""
ELECTRIC VEHICLE model
"""

from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block
import pyomo.environ as pyo

def create_block(b,g):
    #.. section:: SETS
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    b.TIME_before_s = Set(initialize=b.model().TIME_before_s)
    b.bigM_p = Param(initialize=b.model().bigM_p)
    b.timestep_size_p = Param(initialize=b.model().timestep_size_p) # [hours] Duration of the timestep 
    
    # TIME-INDEPENDENT PARAMETERS
    b.permanence_p = Param(within=NonNegativeIntegers)    #:param permanence_p: [timestep] number of timesteps in which the EV can stay 
    b.power_max = Param(within=NonNegativeReals)   #:param power_max: [kW] max power that can be provided to the EV in 1 timestep
    b.arrival_p = Param(within=NonNegativeIntegers) #:param arrival_p: [timestep] value of the timestep in which the EV arrive
    b.power_TotalDemand_p = Param(within=NonNegativeReals) #:param power_TotalDemand_p: [kW] total demand of the EV
        
        
    # .. section:: TIME-DEPENDENT PARAMETERS
    
    @b.Param (b.TIME_s, within=NonNegativeIntegers)
    def presence_p (b,t): #:param presence_p: [timestep] timesteps in which the EV is connected to the micro-grid [1]=EV connected
        value = 0 
        if t in range(pyo.value(b.arrival_p),pyo.value(b.arrival_p+b.permanence_p)+1):
            value = 1 
        return value
   
    
    # .. section:: VARS
    b.power_Charged_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_Charged_v: [kW] power charged into the EV
          
        
    
    #CONSTRAINTS
    @b.Constraint(b.TIME_s)
    def ElectricalPower_demand_calc(b,t):
        return b.power_Charged_v[t] <= b.presence_p[t]*b.power_max 
        
    @b.Constraint()
    def ElectricityDemand_calc(b):
        return b.power_TotalDemand_p <= sum(b.power_Charged_v[t] for t in b.TIME_s)