# Newton自动化脚本

此脚本是一个针对于morelogin而编写，该种前端行为更为安全，用于在Newton执行扫雷游戏和扔骰子。

## 功能

- 自动玩扫雷游戏、参与骰子抽奖
- 支持多环境并发执行


## 说明

### config.json

- "appId"、"secretKey"在morelogin主界面右上角API点击查看
- "baseUrl": "http://127.0.0.1:40000"默认不用修改
- "maxInstances"最大并发实例数，"delayBetweenStartMs"每个实例启动间隔
- "delayBetweenRoundsSeconds"每轮执行间隔

### env.json

- "uniqueId"环境序号，"envId"环境ID（环境id优先级高于前者）
- 环境id在主界面操作列的三个小点可以复制id

## 注意

### 首次运行脚本前要在morelogin登陆过newton


## 运行步骤

1. 安装必要的依赖库:
   ```
   pip install -r requirements.txt
   ```
2. 运行主程序:
   ```
   python main.py
   ```

## 注意事项

- 确保网络连接稳定 
- 环境ID必须有效
- 程序运行时不要操作浏览器窗口