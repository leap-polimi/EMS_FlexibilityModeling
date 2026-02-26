# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - BESS block - fast piecewise approach
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

from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block, Reals, NonPositiveReals
import pyomo.environ as pyo

def create_block(b,g):
    #SETS
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    b.TIME_before_s = Set(initialize=b.model().TIME_before_s)
    b.bigM_p = Param(initialize=b.model().bigM_p)
    b.timestep_size_p = Param(initialize=b.model().timestep_size_p) # [hours] Duration of the timestep 
    # b.costant_penalty_p = Param(initialize=b.model().costant_penalty_p)
    b.costant_penalty_p = Param(initialize=1.0) #:param costant_penalty_p: constant penalty to scale penalties in the objective function
    # .. section:: TIME-INDEPENDENT PARAMETERS
    
    # Look-Up Table (performance map)
    b.dimension_chargeLut_p = Param(within=NonNegativeIntegers) #:param dimension_chargeLut_p: [-] number of points for the charge look-up table
    
    def vertex_chargeLut_s_def(b):
       return range(1,pyo.value(b.dimension_chargeLut_p)+1) 
    b.vertex_chargeLut_s = Set(initialize=vertex_chargeLut_s_def)
    
    b.dimension_dischargeLut_p = Param(within=NonNegativeIntegers) #:param dimension_dischargeLut_p: [-] number of points for the discharge look-up table
    
    
    def vertex_dischargeLut_s_def(b):
        return range(1,pyo.value(b.dimension_dischargeLut_p)+1)
    b.vertex_dischargeLut_s = Set(initialize=vertex_dischargeLut_s_def)
       
    
    
    b.energy_nominal_p = Param(within=NonNegativeReals) # :param energy_nominal_p: [kWh_el] Nominal energy of the BESS
    b.power_nominal_p = Param(within=NonNegativeReals) # :param power_nominal_p: [kW_el] Nominal power of BESS
    b.efficiency_mean_p = Param(within=NonNegativeReals, default = 0.95) # :param efficiency_mean_p: [pu] Mean efficiency of the BESS (used in Capacity Retention calculation)
    
    # Depth of charge/discharge limits
    b.energy_socMin_p = Param(within=NonNegativeReals, default=0) # :param energy_socMin_p: [pu] minimum State of Charge, in terms of per-unit of nominal energy
    b.energy_socMax_p = Param(within=NonNegativeReals, default=1) # :param energy_socMax_p: [pu] maximum State of Charge, in terms of per-unit of nominal energy
    
    # For improving CR reliability it is possible to impose more stringent limits on the SOC
    b.energy_socMinCR_p = Param(within=NonNegativeReals, default=0) # :param energy_socMinCR_p: [pu] minimum State of Charge for CR, in terms of per-unit of nominal energy
    b.energy_socMaxCR_p = Param(within=NonNegativeReals, default=1) # :param energy_socMaxCR_p: [pu] maximum State of Charge for CR, in terms of per-unit of nominal energy
    
    # auxiliaries calculation
    b.auxiliaries_gamma1_p = Param(within=NonNegativeReals, default=25.5) # :param auxiliaries_gamma1_p: 
    b.auxiliaries_gamma2_p = Param(within=NonNegativeReals, default=38) # :param auxiliaries_gamma2_p: 
    b.auxiliaries_rho1_p = Param(within=NonNegativeReals, default=6.2) # :param auxiliaries_rho1_p:
    b.auxiliaries_rho2_p = Param(within=NonNegativeReals, default=265) # :param auxiliaries_rho2_p:
    
    # max cycle number calculation
    b.logic_isCycleLimitOn_p = Param(within=Binary, default=0) # :param logic_isCycleLimitOn_p: [0/1] 1 = activate maximum cycle limit; 0 = no equivalent cycle limit)
    b.cycle_maxNumber_p = Param(within=NonNegativeReals) # :param cycle_maxNumber_p: [-] Maximum number of allowed equivalent cycle in the optimization window

    # BESS thresholds
    b.power_threshold_p = Param(within=NonNegativeReals, default=0) # :param power_threshold_p: [pu] Minimum allowed value of charge/discharge power (AC) in terms of per-unit of the nominal power
       
    # LUT - Discharge phase
    b.power_dischargeDC_p = Param(b.vertex_dischargeLut_s) # :param power_dischargeDC_p: [pu] DC discharge power as per-unit of nominal power
    b.power_dischargeAC_p = Param(b.vertex_dischargeLut_s) # :param power_dischargeAC_p: [pu] AC discharge power as per-unit of nominal power
    b.energy_dischargeSoc_p = Param(b.vertex_dischargeLut_s) # :param energy_dischargeSoc_p: [pu] State of Charge, as per-unit of nominal energy
    
    # LUT - Charge phase
    b.power_chargeDC_p = Param(b.vertex_chargeLut_s) # :param power_chargeDC_p: [pu] DC charge power as per-unit of nominal power
    b.power_chargeAC_p = Param(b.vertex_chargeLut_s) # :param power_chargeAC_p: [pu] AC charge power as per-unit of nominal power
    b.energy_chargeSoc_p = Param(b.vertex_chargeLut_s) # :param power_chargeAC_p: [pu] State of Charge, as per-unit of nominal energys
    
    # LUT - Capability Curve
    b.dimension_lutCapability_p = Param(within=NonNegativeIntegers) # :param dimension_lutCapability_p: [-] Number of points of the capability look-up table
    
    def vertex_lutCapability_s_def(b):
        return range(1,pyo.value(b.dimension_lutCapability_p)+1)
    b.vertex_lutCapability_s = Set(initialize=vertex_lutCapability_s_def)
    
    def step_lutCapability_s_def(b):
        return range(1,pyo.value(b.dimension_lutCapability_p))
    b.step_lutCapability_s = Set(initialize=step_lutCapability_s_def)

    # Capability Curve
    b.energy_socCapability_p = Param(b.vertex_lutCapability_s) # :param energy_socCapability_p: [pu] State of Charge, as per unit of nominal SoC
    b.power_dischargeCapability_p = Param(b.step_lutCapability_s) # :param power_dischargeCapability_p: [pu] Discharge power (AC) as per unit of nominal power
    b.power_chargeCapability_p = Param(b.step_lutCapability_s) # :param power_chargeCapability_p: [pu] Discharge power (AC) as per unit of nominal power
    
    b.logic_isSlackAllowed_p = Param(within=Binary, default=0) # :param logic_isSlackAllowed: 1 = slack is allowed in controllability constraints; 0 = slack is not allowed in controllability constraint

    # .. section:: INITIALIZATION PARAMETERS
    
    b.energy_socFirstTimestep_p = Param(within=NonNegativeReals, default=0.5) # :param energy_socFirstTimestep_p: [pu] SOC at the beginning of first timestep, as per-unit of the nominal energy
    b.energy_socLastTimestep_p = Param(within=NonNegativeReals, default=0.5) # :param energy_socLastTimestep_p: [pu] SOC at the end of the last timestep, as per-unit of the nominal energy
    b.logic_isLastSoc_enforced_p = Param(within=Binary, default=0) # :param logic_isLastSoc_enforced_p: [0/1] 1 = enforce SOC at the end of the last timestep; 0 = do not enforce SOC at the end of the last timestep

    @b.Param(b.TIME_before_s, within=NonNegativeReals) # :param energy_before_p: [kW_el] energy content of the BESS outside optimization window
    def energy_before_p(b,t):
        return b.energy_socFirstTimestep_p*b.energy_nominal_p  
    
    @b.Param(b.TIME_before_s, within=NonNegativeReals) # :param energy_soc_before_p: [pu] energy content in terms of per-unit of nominal energy outside of optimization window
    def energy_soc_before_p(b,t):
        return b.energy_before_p[t] / b.energy_nominal_p
    
    b.cost_minRevenuesCycle_p = Param(within=NonNegativeReals) #:param cost_minRevenuesCycle_p: [€/cycle] cost for each cycle of the BESS
    b.cost_operationMaintenanceEnergy_p = Param(within=NonNegativeReals) #:param cost_operationMaintenanceEnergy_p: [€/kWh] O&M of the battery
    
    # .. section:: TIME-DEPENDENT PARAMETERS
    
    b.timestep_endOfTauUp_p = Param(b.TIME_s, within=NonNegativeIntegers) # :param timestep_endOfTauUp_p: [-] timesteps for upwards capacity retention windows; 
    b.timestep_endOfTauDown_p = Param(b.TIME_s, within=NonNegativeIntegers) # :param timestep_endOfTauDown_p: [-] timesteps for downwards capacity retention windows; 
    b.logic_isAvailable_p = Param(b.TIME_s, within=Binary, default=1) # :param logic_isAvailable_p: [-] 1 = BESS is available; 0 = BESS is not available 
    b.logic_isControllableSoc_p = Param(b.TIME_s, within=Binary, default=1 ) # :param logic_isControllableSoc_p: [-] 1 = BESS soc is controllable by EMS; 0 = BESS must follow external setpoint for SOC
    b.logic_isControllablePowerCharge_p = Param(b.TIME_s, within=Binary, default=1) # :param logic_isControllablePowerCharge_p: [-] 1 = BESS charge is controllable by EMS; 0 = BESS must follow external setpoint for charge power
    b.logic_isControllablePowerDischarge_p = Param(b.TIME_s, within=Binary, default=1) # :param logic_isControllablePowerDischarge_p: [-] 1 = BESS charge is controllable by EMS; 0 = BESS must follow external setpoint for charge power
    b.energy_setpointSoc_p = Param(b.TIME_s, within=NonNegativeReals,default=0.0) # :param energy_setpointSoc_p: [pu] External Setpoint for SOC
    b.power_setpointChargeAC_p = Param(b.TIME_s, within=NonNegativeReals,default=0.0) #:param power_setpointChargeAC_p: [pu] External Setpoint for Power Charge AC
    b.power_setpointDischargeAC_p = Param(b.TIME_s, within=NonNegativeReals,default=0.0) #:param power_setpointDischargeAC_p: [pu] External Setpoint for Power Charge AC

    b.logic_isAsmAllowed_p = Param (b.TIME_s, within = Binary, default=1) #:param logic_isAsmAllowed_p: [1] device is allowed to participate into ASM 
    b.penalty_slack_p = Param(b.TIME_s,within=NonNegativeReals, default=1000) #:param penalty_slack_p: [€/kWh] cost associated to the usage of slack variables 
    # .. section:: VARS
    
    b.temperature_external_v = Var(b.TIME_s, within=NonNegativeReals) # :param temperature_external_v: [°C] External Temperature - TO BE CONSTRAINED FROM OUTSIDE
    
    b.energy_soc_v = Var(b.TIME_s, within=NonNegativeReals) # :param energy_soc_v: [pu] Current State of Charge of the BESS, in terms of per-unit of nominal energy
    b.energy_v = Var(b.TIME_s, within=NonNegativeReals) # :param energy_v: [kWh_el] Current Energy level of the BESS
    
    b.quantity_numberCycle_v = Var(b.TIME_s, within=NonNegativeReals)                                       #:param quantity_numberCycle_v: [#] Number of cycle
    
    b.energy_socIdle_v = Var(b.TIME_s, within=NonNegativeReals) # :param energy_socIdle_v: [pu] Energy level of the battery while idle, in terms of per-unit of nominal energy
    b.power_dischargeDC_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_dischargeDC_v: [pu] Power discharged from the battery in current timestep (DC side), in terms of per-unit of nominal power
    b.power_dischargeAC_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_dischargeAC_v: [pu] Power discharged from the battery in current timestep (AC side), in terms of per-unit of nominal power    
    
    b.power_chargeDC_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_chargeDC_v: [pu] Power charged into the battery in current timestep (DC side), in terms of per-unit of nominal power
    b.power_chargeAC_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_chargeAC_v: [pu] Power charged into the battery in current timestep (DC side), in terms of per-unit of nominal power    
    
    b.logic_dischargeLutPointWeight_v = Var(b.vertex_dischargeLut_s, b.TIME_s, within=NonNegativeReals) # :param logic_dischargeLutPointWeight_v: [-] linear convex envelope points - discharging phase [0-1]
    b.logic_chargeLutPointWeight_v = Var(b.vertex_chargeLut_s, b.TIME_s, within=NonNegativeReals) # :param logic_chargeLutPointWeight_v: [-] linear convex envelope points - charging phase [0-1]
    
    b.logic_isDischarging_v = Var(b.TIME_s, within=Binary) # :param logic_isDischarging_v: [-] 1 = The battery is discharging in this timestep
    b.logic_isCharging_v = Var(b.TIME_s, within=Binary) # :param logic_isCharging_v: [-] 1 = The battery is charging in this timestep
    b.logic_isIdle_v = Var(b.TIME_s, within=Binary) # :param logic_isIdle_v: [-] 1 = The battery is idle during this timestep
    
    b.power_aux_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_aux_v: [kW] auxiliary consumption of the battery


    b.power_dischargeMax_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_dischargeMax_v: [pu] max discharge power of the BESS (AC side)
    b.power_chargeMax_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_chargeMax_v: [pu] max charge power of the BESS (AC side)
    
    b.logic_dischargeLutStepSelectionCapability_v= Var(b.step_lutCapability_s, b.TIME_s, within=Binary) # :param logic_dischargeLutStepSelectionCapability_v: [-] Select piece of capability curve - discharging phase
    b.logic_chargeLutStepSelectionCapability_v= Var(b.step_lutCapability_s, b.TIME_s, within=Binary) # :param logic_chargeLutStepSelectionCapability_v: [-] Select piece of capability curve - charging phase
    
    
    b.power_virtualCapacityRetentionUp_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_virtualCapacityRetentionUp_v: [kW] power available for capacity retention upward during discharge phase
    b.power_virtualCapacityRetentionDown_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_virtualCapacityRetentionDown_v: [kW] power available for capacity retention downward during charge phase
    
    b.power_capacityRetentionUp_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_capacityRetentionUp_v: [kW] power available for Capacity Retention (AC side)
    b.power_capacityRetentionDown_v = Var(b.TIME_s, within=NonNegativeReals) # :param power_capacityRetentionDown_v: [kW] power available for Capacity Retention (AC side)
      
    # slack handling in controllability constraints
    b.energy_slackSoc_v = Var(b.TIME_s, within=NonNegativeReals) #:param energy_slackSoc_v: [pu] slack variable for SOC controllability
    b.energy_slackCharge_v = Var(b.TIME_s, within=NonNegativeReals) #:param energy_slackCharge_v: [pu] slack variable for power charge controllability
    b.energy_slackDischarge_v = Var(b.TIME_s, within=NonNegativeReals) #:param energy_slackDischarge_v: [pu] slack variable for powerdischarge  controllability
    
    b.energy_slackSoc_positive_v = Var(b.TIME_s, within=NonNegativeReals) #:param energy_slackSoc_positive_v: [pu] positive slack while following SOC setpoint
    b.energy_slackSoc_negative_v = Var(b.TIME_s, within=NonPositiveReals) #:param energy_slackSoc_negative_v: [pu] negative slack while following SOC setpoint
    
    b.power_slackCharge_positive_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_slackCharge_positive_v: [pu] positive slack while following power charge setpoint
    b.power_slackCharge_negative_v = Var(b.TIME_s, within=NonPositiveReals) #:param power_slackCharge_negative_v: [pu] negative slack while following power charge setpoint
    
    b.power_slackDischarge_positive_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_slackDischarge_positive_v: [pu] positive slack while following power discharge setpoint
    b.power_slackDischarge_negative_v = Var(b.TIME_s, within=NonPositiveReals) #:param power_slackDischarge_negative_v: [pu] negative slack while following power discharge setpoint
    
    b.penalty_slack_v = Var(within=NonNegativeReals) #:param penalty_slack_v: [€] total penalty for not following external setpoints
    
    b.cost_operationMaintenance_v = Var(within=NonNegativeReals) #:param cost_operationMaintenance_v: [€] Total cost for O&M incurred by the BESS
    b.cost_minRevenuesCycle_v = Var(within=NonNegativeReals) #:param cost_minRevenuesCycle_v: [€] Tpenalty for cycling the battery
    
    # CONSTRAINTS
   
    # Power discharged - DC side 
    @b.Constraint(b.TIME_s)
    def power_discharge_DC_calc(b,t):
        val = sum(b.power_dischargeDC_p[k]*b.logic_dischargeLutPointWeight_v[k,t] for k in b.vertex_dischargeLut_s)
        return b.power_dischargeDC_v[t] == val
    
    # Power discharged - AC side
    @b.Constraint(b.TIME_s)
    def power_discharge_AC_calc(b,t):
        val = sum(b.power_dischargeAC_p[k]*b.logic_dischargeLutPointWeight_v[k,t] for k in b.vertex_dischargeLut_s)
        return b.power_dischargeAC_v[t] == val
    
    
    # Power charged - DC side 
    @b.Constraint(b.TIME_s)
    def power_charge_DC_calc(b,t):
        val = sum(b.power_chargeDC_p[k]*b.logic_chargeLutPointWeight_v[k,t] for k in b.vertex_chargeLut_s)
        return b.power_chargeDC_v[t] == val
    
    # Power charged - AC side
    @b.Constraint(b.TIME_s)
    def power_charge_AC_calc(b,t):
        val = sum(b.power_chargeAC_p[k]*b.logic_chargeLutPointWeight_v[k,t] for k in b.vertex_chargeLut_s)
        return b.power_chargeAC_v[t] == val
    
    # SOC variation
    @b.Constraint(b.TIME_s)
    def soc_variation_calc(b,t):
        val = \
            sum(b.energy_chargeSoc_p[k]*b.logic_chargeLutPointWeight_v[k,t] for k in b.vertex_chargeLut_s) \
          + sum(b.energy_dischargeSoc_p[k]*b.logic_dischargeLutPointWeight_v[k,t] for k in b.vertex_dischargeLut_s)\
          + b.energy_socIdle_v[t]
        return b.energy_soc_v[t] == val
     
    # SOC calculation    
    @b.Constraint(b.TIME_s)
    def soc_calc(b,t):
        val = b.energy_v[t] / b.energy_nominal_p
        return b.energy_soc_v[t] == val
    
    # Idle SOC calculation - 0 if the battery is not idle
    @b.Constraint(b.TIME_s)
    def idle_soc_calc(b,t):
        return b.energy_socIdle_v[t] <= b.logic_isIdle_v[t]*b.bigM_p
    
     
    # Determine if the battery is discharging       
    @b.Constraint(b.TIME_s)
    def discharge_calc(b,t):
        val = sum(b.logic_dischargeLutPointWeight_v[k,t] for k in b.vertex_dischargeLut_s)
        return b.logic_isDischarging_v[t] == val
        
    # Determine if the battery is charging  
    @b.Constraint(b.TIME_s)
    def charge_calc(b,t):
        val = sum(b.logic_chargeLutPointWeight_v[k,t] for k in b.vertex_chargeLut_s)
        return b.logic_isCharging_v[t] == val
    
    # Battery can either be charging, discharging or idle 
    @b.Constraint(b.TIME_s)
    def charge_discharge_idle_dicotomy(b,t):
        return b.logic_isCharging_v[t] + b.logic_isDischarging_v[t] + b.logic_isIdle_v[t] == 1
    
    
    # Energy content variation
    @b.Constraint(b.TIME_s)
    def energy_variation_calc(b,t):
        if t == b.TIME_s.first():
            prev_t = b.TIME_before_s.last()
            val = \
                b.energy_before_p[prev_t] \
              + (b.power_chargeDC_v[t] - b.power_dischargeDC_v[t])*b.power_nominal_p*b.timestep_size_p
        else:
            prev_t = b.TIME_s.prev(t)
            val = \
                b.energy_v[prev_t] \
              + (b.power_chargeDC_v[t] - b.power_dischargeDC_v[t])*b.power_nominal_p*b.timestep_size_p
        return b.energy_v[t] == val
    
    # Energy at the end of day (can be left free for multiple days simulation)
    @b.Constraint()
    def energy_endOfDay(b):
        if b.logic_isLastSoc_enforced_p == 1:
            return b.energy_v[b.TIME_s.last()] == b.energy_socLastTimestep_p*b.energy_nominal_p
        else:
            return Constraint.Skip
    
    
    # Capability curve - Step selection during charge
    @b.Constraint(b.TIME_s)
    def capability_charge_calc(b,t):
        return 1 == sum(b.logic_chargeLutStepSelectionCapability_v[k,t] for k in b.step_lutCapability_s)
    
    # Capability curve - Step selection during discharge
    @b.Constraint(b.TIME_s)
    def capability_discharge_calc(b,t):
        return 1 == sum(b.logic_dischargeLutStepSelectionCapability_v[k,t] for k in b.step_lutCapability_s)
    
    # Capability curve - soc calculation during charge phase - Lower Bound
    @b.Constraint(b.TIME_s)
    def soc_chargeLower_calc(b,t):
        return b.energy_soc_v[t] >= sum(b.energy_socCapability_p[k]*b.logic_chargeLutStepSelectionCapability_v[k,t] for k in b.step_lutCapability_s)
    
    # Capability curve - soc calculation during charge phase - upper bound
    @b.Constraint(b.TIME_s)
    def soc_chargeUpper_calc(b,t):
        return b.energy_soc_v[t] <= sum(b.energy_socCapability_p[k+1]*b.logic_chargeLutStepSelectionCapability_v[k,t] for k in b.step_lutCapability_s)


    # Capability curve - soc calculation during discharge phase - Lower Bound
    @b.Constraint(b.TIME_s)
    def soc_dischargeLower_calc(b,t):
        return b.energy_soc_v[t] >= sum(b.energy_socCapability_p[k]*b.logic_dischargeLutStepSelectionCapability_v[k,t] for k in b.step_lutCapability_s)


    # Capability curve - soc calculation during discharge phase - upper bound
    @b.Constraint(b.TIME_s)
    def soc_dischargeUpper_calc(b,t):
        return b.energy_soc_v[t] <= sum(b.energy_socCapability_p[k+1]*b.logic_dischargeLutStepSelectionCapability_v[k,t] for k in b.step_lutCapability_s)

    # Capability curve - max power discharging calculation
    @b.Constraint(b.TIME_s)
    def power_dischargeMax_calc(b,t):
        val = sum(b.power_dischargeCapability_p[k]*b.logic_dischargeLutStepSelectionCapability_v[k,t] for k in b.step_lutCapability_s)
        return b.power_dischargeMax_v[t] == val

    # Capability curve - max power charging calculation
    @b.Constraint(b.TIME_s)
    def power_chargeMax_calc(b,t):
        val = sum(b.power_chargeCapability_p[k]*b.logic_chargeLutStepSelectionCapability_v[k,t] for k in b.step_lutCapability_s)
        return b.power_chargeMax_v[t] == val
    
    # Capability curve - discharge power limitation
    @b.Constraint(b.TIME_s)
    def power_discharge_limit(b,t):
        return b.power_dischargeAC_v[t] <= b.power_dischargeMax_v[t]

    # Capability curve - charge power limitation
    @b.Constraint(b.TIME_s)
    def power_charge_limit(b,t):
        return b.power_chargeAC_v[t] <= b.power_chargeMax_v[t]


    # Power for auxiliaries consumption (e.g. A/C)
    @b.Constraint(b.TIME_s)
    def power_auxiliaries_calc(b,t):
        return b.power_aux_v[t] == (b.auxiliaries_gamma1_p*b.temperature_external_v[t] + b.auxiliaries_gamma2_p + b.auxiliaries_rho1_p*((b.power_dischargeAC_v[t] + b.power_chargeAC_v[t]) * b.power_nominal_p) + b.auxiliaries_rho2_p) / 1000


    # Soc lower bound (depth of discharge)
    @b.Constraint(b.TIME_s)
    def soc_lowerBound_limit(b,t):
        return b.energy_socMin_p <= b.energy_soc_v[t]
    
    
    # Soc upper bound (depth of charge)
    @b.Constraint(b.TIME_s)
    def soc_upperBound_limit(b,t):
        return b.energy_soc_v[t] <= b.energy_socMax_p
    
    # Limit on number of equivalent cycles
    @b.Constraint()
    def equivalent_cycle_limit(b):
        if b.logic_isCycleLimitOn_p == 1:
            return b.cycle_maxNumber_p >= ((sum([b.power_dischargeDC_v[t] for t in b.TIME_s]) + sum([b.power_chargeDC_v[t] for t in b.TIME_s]))*b.timestep_size_p/2*b.power_nominal_p/b.energy_nominal_p)/(b.energy_socMax_p - b.energy_socMin_p)
        else:
            return Constraint.Skip
        
    @b.Constraint(b.TIME_s)
    def virtual_capacity_retention_up_limit1(b,t):
        return b.power_virtualCapacityRetentionUp_v[t] <= (b.power_dischargeMax_v[t] - b.power_dischargeAC_v[t])*b.power_nominal_p
        
    @b.Constraint(b.TIME_s)
    def virtual_capacity_retention_up_limit2(b,t):
        if (b.timestep_endOfTauUp_p[t] != 0):
            prev_soc = 0
            if t == b.TIME_s.first():
                prev_soc = b.energy_soc_before_p[b.TIME_before_s.last()]
            else:
                prev_soc = b.energy_soc_v[b.TIME_s.prev(t)]
            
            return sum(b.power_virtualCapacityRetentionUp_v[tau]*b.timestep_size_p + b.power_nominal_p*b.power_dischargeAC_v[tau]*b.timestep_size_p for tau in range(t,b.timestep_endOfTauUp_p[t])) \
                <= (prev_soc - b.energy_socMinCR_p.value)*b.energy_nominal_p.value*b.efficiency_mean_p.value
        else:
            return Constraint.Skip
        

    @b.Constraint(b.TIME_s)
    def virtual_capacity_retention_down_limit1(b,t):
        return b.power_virtualCapacityRetentionDown_v[t] <= (b.power_chargeMax_v[t] - b.power_chargeAC_v[t])*b.power_nominal_p


    @b.Constraint(b.TIME_s)
    def virtual_capacity_retention_dw_limit2(b,t):
        if (b.timestep_endOfTauDown_p[t] != 0):
            prev_soc = 0
            if t == b.TIME_s.first():
                prev_soc = b.energy_soc_before_p[b.TIME_before_s.last()]
            else:
                prev_soc = b.energy_soc_v[b.TIME_s.prev(t)]
            return sum(b.power_virtualCapacityRetentionDown_v[tau]*b.timestep_size_p + b.power_nominal_p*b.power_chargeAC_v[tau]*b.timestep_size_p for tau in range(t,b.timestep_endOfTauDown_p[t])) \
                <= (b.energy_socMaxCR_p - prev_soc)*b.energy_nominal_p
        else:
            return Constraint.Skip
        
    @b.Constraint(b.TIME_s)
    def capacity_retention_up_calc(b,t):
        return b.power_capacityRetentionUp_v[t] <= b.power_chargeAC_v[t]*b.power_nominal_p + b.power_virtualCapacityRetentionUp_v[t]
    
    @b.Constraint(b.TIME_s)
    def capacity_retention_down_calc(b,t):
        return b.power_capacityRetentionDown_v[t] <= b.power_dischargeAC_v[t]*b.power_nominal_p + b.power_virtualCapacityRetentionDown_v[t]

    @b.Constraint(b.TIME_s)
    def ASM_allowed_UP(b,t):
        if b.logic_isAsmAllowed_p[t] == 0:
            return b.power_capacityRetentionUp_v[t] == 0
        else:
            return Constraint.Skip
        
    @b.Constraint(b.TIME_s)
    def ASM_allowed_DOWN(b,t):
        if b.logic_isAsmAllowed_p[t] == 0:
            return b.power_capacityRetentionDown_v[t] == 0
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def availability_charge(b,t):
        return b.power_chargeAC_v[t] <= b.logic_isAvailable_p[t]*b.bigM_p

    @b.Constraint(b.TIME_s)
    def availability_discharge(b,t):
        return b.power_dischargeDC_v[t] <= b.logic_isAvailable_p[t]*b.bigM_p
    
    @b.Constraint(b.TIME_s)
    def threshold_charge(b,t):
        return b.power_chargeAC_v[t] >= b.power_threshold_p*b.logic_isCharging_v[t]
    
    @b.Constraint(b.TIME_s)
    def threshold_discharge(b,t):
        return b.power_dischargeAC_v[t] >= b.power_threshold_p*b.logic_isDischarging_v[t]
    
    @b.Constraint(b.TIME_s)
    def controllability_soc_def(b,t):
        if b.logic_isControllableSoc_p[t] == 1:
            return Constraint.Skip
        else:
            return b.energy_soc_v[t] == b.energy_setpointSoc_p[t] + (b.energy_slackSoc_positive_v[t]+b.energy_slackSoc_negative_v[t])*b.logic_isSlackAllowed_p
                                                                     
    
    @b.Constraint(b.TIME_s)
    def slack_soc_def(b,t):
        return b.energy_slackSoc_v[t] == (b.energy_slackSoc_positive_v[t] - b.energy_slackSoc_negative_v[t])*b.energy_nominal_p
    
    @b.Constraint(b.TIME_s)
    def controllability_power_charge_def(b,t):
        if b.logic_isControllablePowerCharge_p[t] == 1:
            #cross-check for stationary BESS
            if b.logic_isControllablePowerDischarge_p[t] == 0 \
            and b.power_setpointDischargeAC_p[t] == 0.0:
                return b.power_chargeAC_v[t] == 0
            else:
                return Constraint.Skip
        else:
            return b.power_chargeAC_v[t] == b.power_setpointChargeAC_p[t] + (b.power_slackCharge_positive_v[t]+b.power_slackCharge_negative_v[t])*b.logic_isSlackAllowed_p

    
    @b.Constraint(b.TIME_s)
    def slack_charge_def(b,t):
        return b.energy_slackCharge_v[t] == (b.power_slackCharge_positive_v[t] - b.power_slackCharge_negative_v[t])*b.power_nominal_p*b.timestep_size_p
        
    @b.Constraint(b.TIME_s)
    def controllability_power_discharge_def(b,t):
        if b.logic_isControllablePowerDischarge_p[t] == 1:
            #cross-check for stationary BESS
            if b.logic_isControllablePowerCharge_p[t] == 0 \
            and b.power_setpointChargeAC_p[t] == 0.0:
                return b.power_dischargeAC_v[t] == 0
            else:
                return Constraint.Skip
        else:
            return b.power_dischargeAC_v[t] == b.power_setpointDischargeAC_p[t] + (b.power_slackDischarge_positive_v[t]+b.power_slackDischarge_negative_v[t])*b.logic_isSlackAllowed_p

    
    @b.Constraint(b.TIME_s)
    def slack_discharge_def(b,t):
        return b.energy_slackDischarge_v[t] == (b.power_slackDischarge_positive_v[t] - b.power_slackDischarge_negative_v[t])*b.power_nominal_p*b.timestep_size_p

    @b.Constraint()
    def Bess_minRevenuesCycle_cost_calc(b):
        return b.cost_minRevenuesCycle_v == b.cost_minRevenuesCycle_p.value * sum([b.quantity_numberCycle_v[t] for t in b.TIME_s])

    @b.Constraint()
    def Bess_operationMaintenance_cost_calc(b):
        return b.cost_operationMaintenance_v == sum(b.cost_operationMaintenanceEnergy_p*(b.power_dischargeAC_v[t]+b.power_chargeAC_v[t])*b.power_nominal_p*b.timestep_size_p for t in b.TIME_s)
    
    @b.Constraint()
    def slack_penalty_calc(b):
        return b.penalty_slack_v == b.costant_penalty_p * sum((b.energy_slackSoc_v[t] + b.energy_slackCharge_v[t] + b.energy_slackDischarge_v[t])* b.penalty_slack_p[t] for t in b.TIME_s)