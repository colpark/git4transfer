# Node 11 thermal-limit probe

14 September 2026 UTC. Read over SSH from model host `192.168.100.11`, not from node 10. The shell output below is verbatim; blank output after `which tegrastats` means the binary was not found. `sensors` was unavailable.

```text
/sys/class/hwmon/hwmon0/:
device
fan1_input
fan1_target
name
power
power1_input
subsystem
uevent

/sys/class/hwmon/hwmon1/:
device
name
power
subsystem
temp1_input
temp2_input
temp3_input
temp4_input
temp5_input
temp6_input
temp7_input
uevent

/sys/class/hwmon/hwmon2/:
device
name
power
subsystem
temp1_alarm
temp1_crit
temp1_input
temp1_label
temp1_max
temp1_min
temp2_input
temp2_label
temp2_max
temp2_min
temp3_input
temp3_label
temp3_max
temp3_min
uevent

/sys/class/hwmon/hwmon3/:
device
name
power
subsystem
temp1_crit
temp1_highest
temp1_input
temp1_label
temp1_reset_history
uevent

/sys/class/hwmon/hwmon4/:
device
name
power
subsystem
temp1_crit
temp1_highest
temp1_input
temp1_label
temp1_reset_history
uevent

/sys/class/hwmon/hwmon5/:
device
name
power
subsystem
temp1_crit
temp1_highest
temp1_input
temp1_label
temp1_reset_history
uevent

/sys/class/hwmon/hwmon6/:
device
name
power
subsystem
temp1_crit
temp1_highest
temp1_input
temp1_label
temp1_reset_history
uevent

/sys/class/hwmon/hwmon7/:
device
name
power
subsystem
temp1_input
uevent
acpi_fan
acpitz
nvme
mlx5
mlx5
mlx5
mlx5
mt7925_phy0
84850
105000
105000
105000
105000
82850
65261850
65261850
bash: line 1: sensors: command not found
```

Mapping verified by reading each `name` and `temp*_label` alongside the limits: `84850` and `82850` millidegrees Celsius are **NVMe Composite** `crit` and `max`; the four `105000` values are **mlx5 network ASIC** critical limits. `65261850` is exposed for NVMe Sensor 1/2 and is not a credible CPU/SoC limit. `acpitz` has temperature inputs but no `temp*_crit` or `temp*_max`. `tegrastats` and `sensors` are absent. Thus **no readable hardware-authoritative CPU/SoC limit appeared**; no temperature threshold is inferred from these unrelated devices. Use the declared throughput-validity gate.

The exact `which tegrastats && tegrastats --interval 1000` probe produced no stdout/stderr and exited **1** because `which` found no executable; no indefinite `tegrastats` run was started. `sensors` exited **127** with the shell message quoted above.
