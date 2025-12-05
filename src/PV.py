# -*- coding: utf-8 -*-
"""
Photovoltaic Plant (PV) Model
"""

from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block
import pyomo.environ as pyo

def create_block(b,g):
    #SETS
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    
    # TIME-INDEPENDENT PARAMETERS
    
    
    #.. section:: TIME-DEPENDENT PARAMETERS
    b.power_electricityProduction_p = Param(b.TIME_s,within=NonNegativeReals) #:param power_electricityProduction_p: [kW] mean power in timestep
    
    
    #VARS
    
    
    #CONSTRAINTS
   