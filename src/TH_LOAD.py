# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - THERMAL LOAD block
Copyright (C) 2020-2024 LEAP - Authors: M.Zatti, M. Gabba, F. Bovera

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
    
    # TIME-INDEPENDENT PARAMETERS
    
    
    #.. section:: TIME-DEPENDENT PARAMETERS
    b.power_heatDemand_p = Param(b.TIME_s,within=NonNegativeReals) #:param power_heatDemand_p: [kW] mean power in timestep
    
    
    #VARS
    
    
    #CONSTRAINTS
