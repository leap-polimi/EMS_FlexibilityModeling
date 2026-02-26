# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - POD (Point of Delivery) block
Copyright (C) 2020-2024 LEAP scarl
Authors:
- Matteo Zatti
- Marco Gabba
- Filippo Bovera

Modifications in this fork are authored by:
- Andrea Scrocca
- Filippo Bovera
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

from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block, NonPositiveReals
import pyomo.environ as pyo

def create_block(b,g):
    #SETS
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    
    b.timestep_size_p = Param(initialize=b.model().timestep_size_p) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    b.bigM_p = Param(initialize=b.model().bigM_p)
    b.logic_schedulingReschedulingSelection_p = Param(initialize=b.model().logic_schedulingReschedulingSelection_p)
    # b.costant_penalty_p = Param(initialize=b.model().costant_penalty_p)
    b.costant_penalty_p = Param(initialize=1.0) #:param costant_penalty_p: constant penalty to scale penalties in the objective function
    b.logic_rescheduling_localGlobalSelection_p = Param(initialize=b.model().logic_rescheduling_localGlobalSelection_p)
    
    #..section:: ELECTRICAL BILL COMPONENTS
    # [€/kWh] components
    b.cost_dispatching_p = Param(within=NonNegativeReals) #:param cost_dispatching_p: Cost for dispatching per unit of energy [€/kWh]
    b.cost_capacityMarketObligations_p = Param(b.TIME_s, within=NonNegativeReals) #:param cost_capacityMarketObligations_p: Cost for capacity market obligations per unit of energy (much greater in annual peak hours declared by TSO) [€/kWh]
    b.cost_energySupply_p = Param(b.TIME_s, within=NonNegativeReals) #:param cost_energySupply_p: Cost for energy supply per unit of energy (it could be a flat or a time-of-use tariff) [€/kWh]
    b.cost_networksObligations_kWh_p = Param(within=NonNegativeReals) #:param cost_networksObligations_kWh_p: cost for network obligations per unit of energy  [€/kWh]
    b.cost_POD_kWh_p = Param(within=NonNegativeReals) #:param cost_POD_kWh_p: cost for POD per unit of energy [€/kWh]

    # [€/kW] components
    b.cost_networksObligations_kW_p = Param(within=NonNegativeReals) #:param cost_networksObligations_kW_p: cost for network obligation per unit of power [€/kW/month]
    b.cost_POD_kW_p = Param(within=NonNegativeReals) #:param cost_POD_kW_p: cost for POD per unit of power [€/kW/month]

    # [€/POD] components
    b.cost_networksObligations_fixed_p = Param(within=NonNegativeReals) #:param cost_networksObligations_Fixed_p: cost for network obligation [€/month]
    b.cost_POD_fixed_p = Param(within=NonNegativeReals) #:param cost_POD_fixed_p: cost for POD [€/month]

    # Taxes
    b.VAT_p = Param(within=NonNegativeReals) #:param VAT_p: VAT rate  [p.u.]
    b.power_gridLossesMT_p = Param(within=NonNegativeReals) #:param power_gridLossesMT_p: rate for grid losses [p.u.]
    b.cost_excise_p = Param(within=NonNegativeReals) #:param cost_excise_p: cost of the excise per unit of CONSUMED energy [€/kWh]
    
    #.. section:: ADDITIONAL TIME-INDEPENDENT PARAMETERS
    b.power_maxWithdrawnHeritage_p = Param(within=NonNegativeReals)#:param power_maxWithdrawnHeritage_p: [kW] Heritage peak kW withdrawn
    
    b.power_sold_init_p = Param(within=NonNegativeReals) #:param sold_init_p: power sold at the start of optimization [kW]
    b.power_purchased_init_p = Param(within=NonNegativeReals) #:param purchased_init_p: power purchased at the start of optimization [kW] 
    
    b.logic_isPenaltyWithdrawnActive_p = Param(within=Binary, default=0) #:param logic_isPenaltyWithdrawnActive_p: binary [1] minimal withdrawn logics is active
    b.logic_isSlackAllowed_p = Param(within=Binary, default=0) #:param logic_isSlackAllowed_p: 1 = Slacks are allowed while following external setpoint for exchanges
    
    #.. section:: GRID-EXCHANGE PARAMETERS
    b.price_electricityPurchased_p = Param(b.TIME_s, within=NonNegativeReals) #:param price_electricityPurchased_p: [€/kWh] Price of energy purchase 
    b.price_electricitySold_p = Param(b.TIME_s, within=NonNegativeReals) #:param price_electricitySold_p: [€/kWh] Price of energy sale 
    b.logic_isExchangesLock_p = Param(b.TIME_s, within=Binary, default=0) #:param logic_isExchangesLock_p: 0 = prices is not locked
    b.logic_optimizeProfile_p = Param(b.TIME_s, within=Binary, default=1) #:param logic_optimizeProfile_p: 0 = a set point must be provided for exchanges, 1 = the model can optimize exchanges
    b.power_electricityWithdrawn_setpoint_p = Param(b.TIME_s, within=NonNegativeReals, default=0.0) #:param power_electricityWithdrawn_setpoint_p: [kW] setpoint for electricity withdrawn 
    b.power_electricityInjected_setpoint_p = Param(b.TIME_s, within=NonNegativeReals, default=0.0) #:param power_electricityInjected_setpoint_p: [kW] setpoint for electricity Injected 
    b.penalty_withdrawn_p = Param(b.TIME_s,within=NonNegativeReals, default=1000.0) #:param penalty_withdrawn_p: coefficient of penalization for minimal withdrawn track mode
    b.penalty_slack_p = Param(b.TIME_s,within=NonNegativeReals, default=1000.0) #:param penalty_slack_p: [€/kWh] cost associated to the usage of slack variables
    b.imbalance_penalty_p = Param(b.TIME_s,within=NonNegativeReals, default=1000.0) #:param imbalance_penalty_p: [€/kWh] cost associated to imbalances

    #.. section:: RESCHEDULING PARAMETERS
    b.baselineWithdrawn_p =Param(b.TIME_s,within=NonNegativeReals) #:param baselineWithdrawn_p: the scheduled withdrawn 
    b.baselineInjected_p=Param(b.TIME_s,within=NonNegativeReals)  #:param baselineInjected_p: the scheduled purchase
    
    b.logic_IDM_p = Param (b.TIME_s, within=Binary, default=1) #:param logic_IDM_p: binary intraday market active/not active [1,0] - acive when the intraday market is still available, not active when excess energy will result in an imbalance    
    
    
    #.. section:: VARS
    b.power_electricityWithdrawn_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_electricityWithdrawn_v:  [kW] Mean power withdrawal from the grid in the time unit - PHYSICAL EXCHANGE
    b.power_electricityInjected_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_electricityInjected_v: [kW] Mean power injection to the grid in the time unit - PHYSICAL EXCHANGE
    b.logic_isWithdrawing_v = Var(b.TIME_s, within=Binary) #:param logic_isWithdrawing_v: [-] 1 = POD is withdrawing; 0 = POD is injecting
    
    b.power_electricityPurchased_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_electricityPurchased_v: [kW] Mean power purchased from the grid in the time unit - ECONOMICAL EXCHANGE
    b.power_electricitySold_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_electricitySold_v: [kW] Mean power sold to the grid in the time unit - ECONOMICAL EXCHANGE
    b.logic_isPurchasing_v = Var(b.TIME_s, within=Binary) #:param logic_isPurchasing_v: [-] 1 = POD is purchasing; 0 = POD is selling
    
    b.power_maxWithdrawn_v = Var(within=NonNegativeReals) #:param power_maxWithdrawn_v: [kW] Max power withdrawal from the grid in the optimization horizon
    
    b.power_electricityConsumption_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_electricityConsumption_v: [kW] Electricity Consumption (mean power in the timestep) (TO BE CONSTRAINED OUTSIDE)
    b.penalty_withdrawn_v = Var(within=NonNegativeReals) #:param penalty_withdrawn_v: [€] penalty to achieve track mode of minimal withdrawn 
    b.penalty_imbalance_v = Var(within=NonNegativeReals) #:param penalty_imbalance_v: [€] penalty for imbalance in constraints

    # RESCHEDULING VARS
    b.logic_isImbalanceNegative_v = Var(b.TIME_s,within=Binary) #:param logic_isImbalanceNegative_v: binary [1] there is negative imbalance
    b.imbalance_negative_v = Var(b.TIME_s, within=NonNegativeReals) #:param imbalance_negative_v: [kW] negative imbalance
    b.imbalance_positive_v = Var(b.TIME_s, within=NonNegativeReals) #:param imbalance_positive_v: [kW] positive imbalance
    b.logicBDE_Up_v = Var(b.TIME_s, within=Binary) #:param logicBDE_Up_v: [1] the upward BDE is active
    b.logicBDE_Down_v = Var(b.TIME_s, within=Binary) #:param logicBDE_Down_v: [1] the downward BDE is active
    
    # BDE VARS
    b.BDE_Up_v=Var(b.TIME_s,within=NonNegativeReals) #:param BDE_Up_v: [kWel] =1 BDE upward
    b.BDE_Down_v=Var(b.TIME_s,within=NonNegativeReals) #:param BDE_Down_v: [kWel]  =1 BDE downward
    
    # Expense modelization VARS
    b.cost_electricity_capacityMarket_v = Var(b.TIME_s, within=NonNegativeReals) #:var cost_electricity_capacityMarket_v: [€] Expenditures for capacity market component
    b.cost_electricity_supply_v = Var(b.TIME_s, within=NonNegativeReals) #:var cost_electricity_supply_v: [€] Expenditures for energy suppy component
    b.cost_electricity_kWh_var_v = Var(b.TIME_s, within=NonNegativeReals) #:var cost_electricity_kWh_var_v: [€] Total expenditures for €/kWh time-dependent components
    b.cost_electricity_kWh_other_v = Var(b.TIME_s, within=NonNegativeReals) #:var cost_electricity_kWh_other_v: [€] Expenditures for €/kWh time-independent components
    b.cost_electricity_kWh_v = Var(b.TIME_s, within=NonNegativeReals) #:var cost_electricity_kWh_v: [€] Total expenditures for €/kWh components
    b.cost_electricity_kW_v = Var(within=NonNegativeReals) #:var cost_electricity_kW_v: [€] Total expenditures for power component
    b.cost_electricity_fixed_v = Var(within=NonNegativeReals) #:var cost_electricity_fixed_v: [€] Total expenditures for fixed component
    b.cost_electricity_excise_v = Var(b.TIME_s, within=NonNegativeReals) #:var cost_electricity_excise_v: [€] Expenditures for electricity excise on consumpted energy
    b.cost_electricity_v = Var(within=NonNegativeReals) #:var cost_electricity_v: [€] Total expenditures for electricity
    b.revenue_electricity_v = Var(within=NonNegativeReals) #:var revenue_electricity_v: [€] Total revenue from electricity 
    
    #SLACK VARS
    b.power_slackWithdrawn_positive_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_slackWithdrawn_positive_v: [kW] positive slack while following power withdrawn setpoint
    b.power_slackWithdrawn_negative_v = Var(b.TIME_s, within=NonPositiveReals) #:param power_slackWithdrawn_negative_v: [kW] negative slack while following power withdrawn setpoint
    
    b.power_slackInjected_positive_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_slackInjected_positive_v: [kW] positive slack while following power withdrawn setpoint
    b.power_slackInjected_negative_v = Var(b.TIME_s, within=NonPositiveReals) #:param power_slackInjected_negative_v: [kW] negative slack while following power withdrawn setpoint
    
    b.energy_slackInjected_v = Var(b.TIME_s, within= NonNegativeReals) #:param energy_slackInjected_v: [kWh] total slack while following setpoint on injected power
    b.energy_slackWithdrawn_v = Var(b.TIME_s, within= NonNegativeReals) #:param energy_slackWithdrawn_v: [kWh] total slack while following setpoint on withdrawn power
    b.penalty_slack_v = Var(within=NonNegativeReals) #:param penalty_slack_v: [€] total penalty for not following external setpoints

    # VARS describing the Italian Scheme available for BESS negative injected energy (energy withdrawn from the grid for charging and then re-injected into the grid)
    #The negative injected energy can be considered as extempted from certain bill components and valued at the Day-Ahead Market zonal price (ARERA Deliberation 109/2021/R/eel)
    b.power_chargeConsumed_v = Var(b.TIME_s, within=NonNegativeReals) #:var power_chargeConsumed_v: [kWel] fraction of the charging power later consumed by the system
    b.power_chargeInjectedNegative_v = Var(b.TIME_s, within=NonNegativeReals) #:var power_chargeInjectedNegative_v: [kWel] fraction of the charging power later injected into the grid
    b.logic_isCharge_InjectedNegative_v = Var(b.TIME_s, within=Binary) #:param logic_isCharge_InjectedNegative_v: [-] Binary =1 if there is any charging power which could be considered as 'negative injected energy' later (if P_cha> P_prod)

    b.power_dischargeConsumed_v = Var(b.TIME_s, within=NonNegativeReals) #:var power_dischargeConsumed_v: [kWel] fraction of the discharging power consumed by the system
    b.power_dischargeInjectedNegative_v = Var(b.TIME_s, within=NonNegativeReals) #:var power_dischargeInjectedNegative_v: [kWel] fraction of the discharging power which could be considered as injected into the grid
    b.logic_isDischarge_InjectedNegative_v = Var(b.TIME_s, within=Binary) #:param logic_isDischarge_InjectedNegative_v: [-] Binary =1 if there is any discharging power which could be considered as 'negative injected energy' (if P_dis> P_load)

    # To be constrained from other blocks
    b.power_charge_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_charge_v: [kWel] Total BESS charging power
    b.power_discharge_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_discharge_v: [kWel] Total BESS discharging power
    b.power_electricityProduction_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_elProduction_v: [kWel] System electrical production power
    

    
    #CONSTRAINTS
    @b.Constraint(b.TIME_s)
    def max_withdrawn_calc(b,t):
        return b.power_maxWithdrawn_v >= b.power_electricityWithdrawn_v[t]
    
    @b.Constraint()
    def max_withdrawn_calc_2(b):
        return b.power_maxWithdrawn_v >= b.power_maxWithdrawnHeritage_p

    
    # Energy can be withdrawn OR injected
    @b.Constraint(b.TIME_s)
    def phisical_dicotomy_1(b,t):
        return b.power_electricityWithdrawn_v[t] <= b.logic_isWithdrawing_v[t] * b.bigM_p
    
    @b.Constraint(b.TIME_s)
    def phisical_dicotomy_2(b,t):
        return b.power_electricityInjected_v[t] <= (1- b.logic_isWithdrawing_v[t]) * b.bigM_p
                                                      
    # Energy can be sold OR purchased
    @b.Constraint(b.TIME_s)                                                  
    def commercial_dicotomy_1(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return b.power_electricityPurchased_v[t] <= b.logic_isPurchasing_v[t] * b.bigM_p
        else:
            return b.power_electricityPurchased_v[t] <= b.logic_isPurchasing_v[t] * b.logic_IDM_p[t] * b.bigM_p


    @b.Constraint(b.TIME_s)                                                  
    def commercial_dicotomy_2(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return b.power_electricitySold_v[t] <= (1 - b.logic_isPurchasing_v[t]) * b.bigM_p
        else:
            return b.power_electricitySold_v[t] <= (1 - b.logic_isPurchasing_v[t]) * b.logic_IDM_p[t] * b.bigM_p
        
        # imbalance exchange
    @b.Constraint(b.TIME_s)
    def negative_imbalance_def(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.imbalance_negative_v[t] <= b.logic_isImbalanceNegative_v[t] * (1 - b.logic_IDM_p[t]) * b.bigM_p # [kWel]
   
    @b.Constraint(b.TIME_s)
    def positive_imbalance_def(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:   
            return b.imbalance_positive_v[t] <= (1 - b.logic_isImbalanceNegative_v[t]) * (1 - b.logic_IDM_p[t])  * b.bigM_p # [kWel]
    
    # no MROD: 
    #        - no negative unbalance if upward BDE is active
    #        - no positive unbalance if downward BDE is active
    @b.Constraint(b.TIME_s)
    def MROD_UP_def(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.power_electricityPurchased_v[t] <= (1-b.logicBDE_Up_v[t]) * b.bigM_p
    
    @b.Constraint(b.TIME_s)
    def MROD_DW_def(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.power_electricitySold_v[t] <= (1-b.logicBDE_Down_v[t]) * b.bigM_p
        
    @b.Constraint(b.TIME_s)
    def MROD_IMB_UP_def(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.imbalance_negative_v[t] <= (1-b.logicBDE_Up_v[t]) * b.bigM_p
    
    @b.Constraint(b.TIME_s)
    def MROD_IMB_DW_def(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.imbalance_positive_v[t] <= (1-b.logicBDE_Down_v[t]) * b.bigM_p
    
    @b.Constraint(b.TIME_s)
    def MROD_UPdicotomy_1(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.logicBDE_Up_v[t] <= b.BDE_Up_v[t]
    
    @b.Constraint(b.TIME_s)
    def MROD_UPdicotomy_2(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.logicBDE_Up_v[t] * b.bigM_p >= b.BDE_Up_v[t] 
    
    @b.Constraint(b.TIME_s)
    def MROD_DWdicotomy_1(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.logicBDE_Down_v[t] <= b.BDE_Down_v[t]
    
    @b.Constraint(b.TIME_s)
    def MROD_DWdicotomy_2(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return Constraint.Skip
        else:
            return b.logicBDE_Down_v[t] * b.bigM_p >= b.BDE_Down_v[t]
   
    
    @b.Constraint(b.TIME_s)
    def energy_exchanges(b,t):
        physical = b.power_electricityWithdrawn_v[t] - b.power_electricityInjected_v[t]
        commercial = b.power_electricityPurchased_v[t]- b.power_electricitySold_v[t] 
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            ancillary = 0 
            reference_program = 0
            imbalance = 0 
        else: #Rescheduling 
            ancillary = b.BDE_Down_v[t] - b.BDE_Up_v[t]
            reference_program = b.baselineWithdrawn_p[t] - b.baselineInjected_p[t]
            imbalance = b.imbalance_negative_v[t] - b.imbalance_positive_v[t] 
        return physical == commercial + ancillary + reference_program + imbalance
    
    #BESS negative injected energy constraints
    @b.Constraint(b.TIME_s)
    def power_charge_composition(b,t):
        return b.power_charge_v[t] == b.power_chargeConsumed_v[t] + b.power_chargeInjectedNegative_v[t]
    
    @b.Constraint(b.TIME_s)
    def power_discharge_composition(b,t):
        return b.power_discharge_v[t] == b.power_dischargeConsumed_v[t] + b.power_dischargeInjectedNegative_v[t]
    
    @b.Constraint(b.TIME_s)
    def power_charge_injected_negative(b,t):
        value = b.power_charge_v[t] *(1 - b.logic_isCharge_InjectedNegative_v[t]) + b.power_electricityProduction_v[t]*b.logic_isCharge_InjectedNegative_v[t]
        return b.power_chargeConsumed_v[t] >= value
    
    @b.Constraint(b.TIME_s)
    def power_discharge_injected_negative(b,t):
        value = b.power_discharge_v[t] *(1 - b.logic_isDischarge_InjectedNegative_v[t]) + b.power_electricityConsumption_v[t]*b.logic_isDischarge_InjectedNegative_v[t]
        return b.power_dischargeConsumed_v[t] >= value
    
    @b.Constraint(b.TIME_s)
    def power_injected_negative_consistency(b,t):
        value1= sum(b.power_chargeInjectedNegative_v[t] for t in b.TIME_s)
        value2= sum(b.power_dischargeInjectedNegative_v[t] for t in b.TIME_s)
        return value1 == value2
    
    
    # Cost calculation
    # [€/kWh] components    
    @b.Constraint(b.TIME_s)
    def cost_electricity_supply_calc(b,t):
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            value = b.cost_energySupply_p[t]*(b.power_electricityWithdrawn_v[t]-b.power_chargeInjectedNegative_v[t])*b.timestep_size_p + \
                    b.cost_energySupply_p[t]*(b.power_electricityWithdrawn_v[t]-b.power_chargeInjectedNegative_v[t])*b.timestep_size_p*b.power_gridLossesMT_p + \
                    b.price_electricityPurchased_p[t]*b.power_chargeInjectedNegative_v[t]*b.timestep_size_p 
        else: # Global rescheduling: the purchased energy is valued at the IDM energy price
            value = b.price_electricityPurchased_p[t]*b.power_electricityPurchased_v[t]*b.timestep_size_p + \
                    b.price_electricityPurchased_p[t]*b.power_electricityWithdrawn_v[t]*b.timestep_size_p*b.power_gridLossesMT_p 
        return b.cost_electricity_supply_v[t] == value
    
    @b.Constraint(b.TIME_s)
    def cost_electricity_capacityMarket_calc(b, t):
        value = b.cost_capacityMarketObligations_p[t] * b.power_electricityWithdrawn_v[t] * b.timestep_size_p 
        return b.cost_electricity_capacityMarket_v[t] == value
    
    @b.Constraint(b.TIME_s)
    def cost_electricity_kWh_var_calc(b,t):
        return b.cost_electricity_kWh_var_v[t] == b.cost_electricity_supply_v[t]+ b.cost_electricity_capacityMarket_v[t]
    
    @b.Constraint(b.TIME_s)
    def cost_electricity_kWh_other_calc(b,t):
        value = b.cost_dispatching_p*(b.power_electricityWithdrawn_v[t]-b.power_chargeInjectedNegative_v[t])*b.timestep_size_p*(1+b.power_gridLossesMT_p) + \
                (b.cost_POD_kWh_p+b.cost_networksObligations_kWh_p)*(b.power_electricityWithdrawn_v[t]-b.power_chargeInjectedNegative_v[t])*b.timestep_size_p 
        return b.cost_electricity_kWh_other_v[t] == value
    
    @b.Constraint(b.TIME_s)
    def cost_electricity_kWh_calc(b,t):
        return b.cost_electricity_kWh_v[t] == b.cost_electricity_kWh_var_v[t]+ b.cost_electricity_kWh_other_v[t]
    
    # [€/kW] components    
    @b.Constraint()
    def cost_electricity_kW_calc(b):
        value = b.cost_networksObligations_kW_p*(b.power_maxWithdrawn_v-b.power_maxWithdrawnHeritage_p) + \
                b.cost_POD_kW_p*(b.power_maxWithdrawn_v-b.power_maxWithdrawnHeritage_p) 
        return b.cost_electricity_kW_v == value
    
    # [€/POD] components
    @b.Constraint()
    def cost_electricity_fixed_calc(b):
        value = b.cost_networksObligations_fixed_p + \
                b.cost_POD_fixed_p
        return b.cost_electricity_fixed_v == value
    
    # Excise on consumed energy
    @b.Constraint(b.TIME_s)
    def excise_calc(b,t):
        return b.cost_electricity_excise_v[t] == b.cost_excise_p*b.power_electricityConsumption_v[t]*b.timestep_size_p
    
    #Total Bill costs
    @b.Constraint()
    def cost_electricity_calc(b):
        value = (sum(b.cost_electricity_kWh_v[t] for t in b.TIME_s) + \
                sum(b.cost_electricity_excise_v[t] for t in b.TIME_s) + \
                b.cost_electricity_kW_v + b.cost_electricity_fixed_v)*(1+b.VAT_p)
        return b.cost_electricity_v == value
    
    @b.Constraint()
    def revenue_electricity_calc(b):
        return b.revenue_electricity_v == sum(b.price_electricitySold_p[t]*b.power_electricitySold_v[t]*b.timestep_size_p for t in b.TIME_s)
    
    # LOCK VARIABLE VALUES
    @b.Constraint(b.TIME_s)
    def EL_Purchased_LOCK_DEF(b,t): 
        if b.logic_isExchangesLock_p[t] == 0:
            return Constraint.Skip
        else:
            if t == b.TIME_s.first():
                return b.power_electricityPurchased_v[t] == b.power_purchased_init_p
            else:
                return b.power_electricityPurchased_v[t] == b.power_electricityPurchased_v[t-1]
    
    @b.Constraint(b.TIME_s)
    def EL_Sold_LOCK_DEF(b,t):
        if b.logic_isExchangesLock_p[t] == 0:
            return Constraint.Skip
        else:
            if t == b.TIME_s.first():
                return b.power_electricitySold_v[t] == b.power_sold_init_p
            else:
                return b.power_electricitySold_v[t] == b.power_electricitySold_v[t-1]
    
    @b.Constraint(b.TIME_s)
    def Injected_setpoint_def(b,t):
        if b.logic_optimizeProfile_p[t] == 1:
            return Constraint.Skip 
        else:
            return b.power_electricityInjected_v[t] == b.power_electricityInjected_setpoint_p[t] + (b.power_slackInjected_positive_v[t]+b.power_slackInjected_negative_v[t])*b.logic_isSlackAllowed_p
        
    @b.Constraint(b.TIME_s)
    def Withdrawn_setpoint_def(b,t):
        if b.logic_optimizeProfile_p[t] == 1:
            return Constraint.Skip 
        else:
            return b.power_electricityWithdrawn_v[t] == b.power_electricityWithdrawn_setpoint_p[t] + (b.power_slackWithdrawn_positive_v[t]+b.power_slackWithdrawn_negative_v[t])*b.logic_isSlackAllowed_p
     
    @b.Constraint()
    def Penalty_withdrawn(b): #reduce withdrawn of the POD
        return b.penalty_withdrawn_v == b.costant_penalty_p * sum(b.logic_isPenaltyWithdrawnActive_p * b.penalty_withdrawn_p[t]*\
               b.power_electricityWithdrawn_v[t]*b.timestep_size_p for t in b.TIME_s)
     
    @b.Constraint()
    def Imbalance_penalty(b): #avoid the system to imbalance the grid
        if b.logic_schedulingReschedulingSelection_p == 0 or b.logic_rescheduling_localGlobalSelection_p==0:
            return b.penalty_imbalance_v == 0
        else:
            tot_imbalance = sum((b.imbalance_positive_v[t]\
                            + b.imbalance_negative_v[t])*b.timestep_size_p\
                            * b.imbalance_penalty_p[t] for t in b.TIME_s )
            return b.penalty_imbalance_v == tot_imbalance * b.costant_penalty_p
        
    @b.Constraint(b.TIME_s)
    def slack_injected_total_def(b,t):
        return b.energy_slackInjected_v[t] == (b.power_slackInjected_positive_v[t] - b.power_slackInjected_negative_v[t])*b.timestep_size_p
     
    @b.Constraint(b.TIME_s)
    def slack_withdrawn_total_def(b,t):
        return b.energy_slackWithdrawn_v[t] == (b.power_slackWithdrawn_positive_v[t] - b.power_slackWithdrawn_negative_v[t])*b.timestep_size_p
    
    @b.Constraint()
    def slack_penalty_calc(b):
        return b.penalty_slack_v == b.costant_penalty_p * sum((b.energy_slackInjected_v[t] + b.energy_slackWithdrawn_v[t])* b.penalty_slack_p[t] for t in b.TIME_s)