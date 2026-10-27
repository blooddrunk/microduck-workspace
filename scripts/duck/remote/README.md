# remote/ —— 设计为“在鸭子板上运行”的脚本

这里的脚本会被 `scripts/duck/push-duck.sh` 推到鸭子家目录 `~/microduck-tools/`。
在鸭子上执行任何脚本前：

1. `bash -n <脚本>` 确认语法；
2. 通读每一行，确认没有 `reboot`、`systemctl restart`、舵机控制等动作；
3. 涉及写系统（apt/系统路径）的脚本必须先在群里评审。

命名建议：`<作用>-<对象>.sh`，例如 `install-sherpa-asr.sh`、`backup-calibration.sh`。
