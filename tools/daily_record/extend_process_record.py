from copy import deepcopy
from pathlib import Path
import shutil

from docx import Document


PATH = Path(r"F:\gugugaga\06 每日记录\张迪翔 水木51 2025013548 未来工程创新设计 个人过程记录.docx")
BACKUP = PATH.with_name(PATH.stem + "（编辑前备份）.docx")

TEXT_97_A = (
    "今天上午继续拼装课程展示需要的道具房屋，并按照前面确定的基站和水域比例调整房屋位置，检查底板、墙体和救援设备之间是否有足够的展示空间。"
    "下午开始整理用于人员识别的数据。我把拍摄的图片按场景归档，统一标注格式和类别名称，检查标注框是否覆盖完整人体，避免漏标、错标和框线偏移。"
    "这一步虽然看起来只是整理图片，但它直接影响后续YOLO模型能否稳定识别落水者，也让我进一步理解了实体模型、视觉输入和软件调度之间的关系。"
)

TEXT_97_B = (
    "通过拼装道具和数据标注，我把实体展示部分和软件部分联系起来：房屋、基站和水域为仿真提供了场景参照，标注图片则为后续摄像头识别人员位置提供训练数据。"
)

TEXT_98_A = (
    "今天上午继续制作实时搜救程序的网页前端。我围绕任务总览、摄像头画面、人员识别结果、船只状态和控制按钮安排页面结构，目标是让操作者能够在一个界面中看到现场信息并发出调度指令。"
    "同时，我把电脑端程序设计成树莓派程序的复制环境，检查前端与本地视觉服务之间的接口，确认摄像头画面、YOLO识别结果和状态数据能够传递到网页端。"
)

TEXT_98_B = (
    "下午安装并熟悉Blender，为后续仿真模型优化做准备。我下载了Blender 5.2.1，并配置了官方实验性MCP扩展，测试了基站、搜救船、俯视相机和人物模型的基本导入与导出流程。"
    "在整理模型时，我特别注意命名、比例、坐标方向和材质设置，避免模型进入Unity后出现大小不一致、朝向错误或与碰撞范围不匹配的问题。"
)

TEXT_99_A = (
    "今天上午继续优化Blender模型和Unity仿真场景。我调整了基站、搜救船和人物的结构比例，检查船只出入口、泊位和相机视野，并把整理后的模型资源导入仿真工程。"
    "同时，我尝试把更接近真实运动的物理效果加入小船，包括刚体、碰撞体、浮力和水面扰动，观察物理参数变化后船体是否能够保持稳定，以及模型碰撞范围是否会影响救援动作。"
)

TEXT_99_B = (
    "下午继续进行仿真优化和运行验证。我完善了控制室界面和任务统计，让系统能够显示获救比例、等待人数、各船载荷、航程、碰撞次数和任务状态，并增加结果导出功能。"
    "随后用24名待救人员测试四船和三船场景，检查静水、街区水流、浅水和强流条件下的表现。测试中静水和一般水流场景能够完成救援，浅水会按设计拒绝通行，强流场景则保留未完成状态而不伪报成功。"
    "最后，我完成了可执行版本和操作说明的整理，并确认暂停、重置、全屏演示和数据导出等功能可以正常使用。"
)


def replace_first(doc, old, new):
    for p in doc.paragraphs:
        if p.text.strip() == old:
            source_run = next((r for r in p.runs if r.text), None)
            rpr = deepcopy(source_run._element.rPr) if source_run is not None and source_run._element.rPr is not None else None
            for run in list(p.runs):
                p._element.remove(run._element)
            run = p.add_run(new)
            if rpr is not None:
                run._element.insert(0, rpr)
            return
    raise RuntimeError(f"未找到待替换段落: {old}")


shutil.copy2(PATH, BACKUP)
doc = Document(PATH)
replace_first(doc, "今天上午拼装道具房屋", TEXT_97_A)
replace_first(doc, "下午进行数据标注", TEXT_97_B)
replace_first(doc, "注今天上午制作网页前端", TEXT_98_A)
replace_first(doc, "今天下午进行blender建模，为优化仿真做准备", TEXT_98_B)
replace_first(doc, "今天上午优化blender建模，并进行仿真优化尝试。", TEXT_99_A)
replace_first(doc, "下午为仿真接入物理引擎。", TEXT_99_B)
doc.save(PATH)

check = Document(PATH)
dates = [p.text.strip() for p in check.paragraphs if p.text.strip() in {"9.7", "9.8", "9.9"}]
print(f"SAVED={PATH}")
print(f"BACKUP={BACKUP}")
print(f"DATES={dates}")
