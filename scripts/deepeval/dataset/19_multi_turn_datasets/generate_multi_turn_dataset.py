#!/usr/bin/env python3
"""
生成多轮对话评测数据集（扩展版）
每个维度15个独立样本，覆盖更多场景
输出格式兼容 deepeval 框架：每条包含 query, response, reference 字段
"""
import json
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  多轮对话测试样本（扩展版 - 每个维度15个独立样本）
# ═══════════════════════════════════════════════════════════════

MULTI_TURN_SAMPLES = {
    "turn_relevancy": [
        {
            "description": "笔记本电脑购买咨询",
            "conversation": [
                {"role": "user", "content": "我想买一台笔记本电脑，预算5000元左右，主要用于办公和轻度娱乐。"},
                {"role": "assistant", "content": "根据您的需求，我推荐几款5000元左右的轻薄本：1. 联想小新Pro14 2. 华为MateBook D14 3. 小米RedmiBook Pro。这些都有不错的性能和续航。"},
                {"role": "user", "content": "那这些电脑的续航时间大概多久？"},
            ],
            "check_turn": 3,
            "expected": "回答应围绕笔记本电脑续航，不应偏离到无关话题",
        },
        {
            "description": "北京旅游行程规划",
            "conversation": [
                {"role": "user", "content": "请帮我规划一个北京3日游的行程。"},
                {"role": "assistant", "content": "北京3日游建议：第一天游览故宫和天安门广场，第二天去长城和颐和园，第三天参观天坛和胡同。"},
                {"role": "user", "content": "长城去哪个段比较好？"},
                {"role": "assistant", "content": "推荐八达岭长城，交通最方便；或者慕田峪长城，人少一些风景更好。"},
                {"role": "user", "content": "那交通怎么安排？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕长城或北京旅游交通，不应突然切换到其他话题",
        },
        {
            "description": "睡眠问题咨询",
            "conversation": [
                {"role": "user", "content": "最近工作压力很大，晚上总是睡不着。"},
                {"role": "assistant", "content": "听起来您最近状态不太好。可以试试睡前冥想、温水泡脚，或者调整作息时间。"},
                {"role": "user", "content": "我试过这些方法，但效果不明显。"},
                {"role": "assistant", "content": "如果自我调节效果有限，建议咨询专业心理医生。同时可以尝试记录睡眠日记，找出影响睡眠的具体因素。"},
                {"role": "user", "content": "还有什么其他方法可以尝试？"},
            ],
            "check_turn": 5,
            "expected": "回答应继续围绕睡眠问题，提供进一步建议，不应偏离",
        },
        {
            "description": "编程语言选择",
            "conversation": [
                {"role": "user", "content": "Python和Java哪个更适合初学者？"},
                {"role": "assistant", "content": "Python更适合初学者，语法简洁，学习曲线平缓。Java语法较严格，但企业应用广泛。"},
                {"role": "user", "content": "那如果我想做数据分析呢？"},
                {"role": "assistant", "content": "数据分析推荐Python，有pandas、numpy、matplotlib等强大库，生态非常成熟。"},
                {"role": "user", "content": "学习这些需要多长时间？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕Python数据分析学习时间，保持话题相关",
        },
        {
            "description": "AI书籍推荐",
            "conversation": [
                {"role": "user", "content": "请推荐几本关于人工智能的好书。"},
                {"role": "assistant", "content": "推荐几本AI经典书籍：1.《人工智能：一种现代方法》2.《深度学习》3.《机器学习实战》。"},
                {"role": "user", "content": "这些书适合什么水平的人读？"},
                {"role": "assistant", "content": "《人工智能：一种现代方法》适合入门，《深度学习》需要一定数学基础，《机器学习实战》适合有编程基础的读者。"},
                {"role": "user", "content": "那看完这些之后该读什么？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕AI进阶书籍推荐，保持话题相关",
        },
        {
            "description": "健身计划制定",
            "conversation": [
                {"role": "user", "content": "我想开始健身，目标是增肌，每周能去3次健身房。"},
                {"role": "assistant", "content": "增肌计划建议：周一练胸和三头，周三练背和二头，周五练腿和肩。每次训练后补充蛋白质。"},
                {"role": "user", "content": "饮食方面有什么建议？"},
                {"role": "assistant", "content": "增肌饮食：每天摄入1.6-2.2g蛋白质/公斤体重，多吃鸡胸肉、鸡蛋、牛肉。训练后30分钟内补充碳水和蛋白质。"},
                {"role": "user", "content": "那有氧运动需要做吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕健身增肌和有氧运动的关系，保持话题相关",
        },
        {
            "description": "租房咨询",
            "conversation": [
                {"role": "user", "content": "我在北京工作，想在朝阳区租一间一居室，预算4000左右。"},
                {"role": "assistant", "content": "朝阳区一居室4000预算可以考虑：常营、管庄、双桥等区域，或者老小区的一居室。交通便利性不错。"},
                {"role": "user", "content": "这些区域到国贸通勤多久？"},
                {"role": "assistant", "content": "常营到国贸地铁约40分钟，管庄约35分钟，双桥约30分钟。早高峰建议预留额外时间。"},
                {"role": "user", "content": "签约时需要注意什么？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕租房签约注意事项，不应偏离到买房或其他话题",
        },
        {
            "description": "英语学习建议",
            "conversation": [
                {"role": "user", "content": "我想提高英语口语，有什么好的方法？"},
                {"role": "assistant", "content": "提高口语的方法：1. 每天坚持跟读VOA或BBC 2. 找语伴练习 3. 参加英语角 4. 使用语言交换APP。"},
                {"role": "user", "content": "我发音不太准，怎么纠正？"},
                {"role": "assistant", "content": "纠正发音：1. 学习音标和口型 2. 录音对比母语者 3. 使用发音纠正APP如ELSA Speak 4. 找外教一对一纠正。"},
                {"role": "user", "content": "每天练习多久比较合适？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕英语口语练习时长建议，保持话题相关",
        },
        {
            "description": "宠物养护",
            "conversation": [
                {"role": "user", "content": "我养了一只3个月大的金毛，第一次养狗，有什么需要注意的？"},
                {"role": "assistant", "content": "幼犬养护要点：1. 按时接种疫苗和驱虫 2. 选择适合幼犬的狗粮 3. 建立定点排便习惯 4. 适量运动，避免过度。"},
                {"role": "user", "content": "它最近总是咬家具，怎么办？"},
                {"role": "assistant", "content": "幼犬咬家具是换牙期正常现象。建议：1. 提供磨牙玩具 2. 发现咬家具时及时制止并引导到玩具 3. 喷苦味剂在 furniture 上。"},
                {"role": "user", "content": "什么时候可以带它出去遛？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕幼犬外出遛狗的时间和注意事项，保持话题相关",
        },
        {
            "description": "摄影入门",
            "conversation": [
                {"role": "user", "content": "我想学习摄影，预算1万左右，推荐什么相机？"},
                {"role": "assistant", "content": "1万预算推荐：索尼A6400套机、佳能R10套机、富士XS10套机。都是不错的入门选择，各有特色。"},
                {"role": "user", "content": "这些相机拍人像哪个更好？"},
                {"role": "assistant", "content": "人像拍摄推荐佳能R10，色彩直出效果好，肤色还原自然。富士XS10胶片模拟也很有特色。"},
                {"role": "user", "content": "镜头需要另外买吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕相机镜头配置建议，不应偏离到其他摄影设备",
        },
        {
            "description": "面试准备",
            "conversation": [
                {"role": "user", "content": "下周有个互联网公司的产品经理面试，该怎么准备？"},
                {"role": "assistant", "content": "产品经理面试准备：1. 熟悉常见面试题（需求分析、项目管理）2. 准备项目案例 3. 了解目标公司产品 4. 练习结构化表达。"},
                {"role": "user", "content": "面试官一般会问什么类型的问题？"},
                {"role": "assistant", "content": "常见问题类型：1. 自我介绍和经历 2. 产品分析题（如何改进某产品）3. 场景设计题 4. 数据分析题 5. 行为面试题。"},
                {"role": "user", "content": "如果遇到不会回答的问题怎么办？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕面试应对策略，保持话题相关",
        },
        {
            "description": "菜谱咨询",
            "conversation": [
                {"role": "user", "content": "我想学做一道简单的家常菜，推荐一下？"},
                {"role": "assistant", "content": "推荐番茄炒蛋，最简单也最经典。需要：番茄2个、鸡蛋3个、葱花、盐、糖、食用油。"},
                {"role": "user", "content": "具体步骤是什么？"},
                {"role": "assistant", "content": "步骤：1. 番茄切块，鸡蛋打散 2. 热油炒鸡蛋盛出 3. 炒番茄出汁 4. 倒入鸡蛋翻炒 5. 加盐糖调味撒葱花。"},
                {"role": "user", "content": "怎么让番茄更出汁？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕番茄炒蛋的烹饪技巧，保持话题相关",
        },
        {
            "description": "手机选购",
            "conversation": [
                {"role": "user", "content": "想换手机，预算3000-4000，主要拍照和打游戏。"},
                {"role": "assistant", "content": "这个价位推荐：红米K70 Pro、iQOO Neo9 Pro、一加Ace3。都有不错的性能和拍照。"},
                {"role": "user", "content": "这几款拍照哪个最好？"},
                {"role": "assistant", "content": "拍照方面：红米K70 Pro主摄最强，iQOO Neo9 Pro人像不错，一加Ace3综合均衡。看您更注重哪方面。"},
                {"role": "user", "content": "续航怎么样？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕手机续航对比，保持话题相关",
        },
        {
            "description": "理财规划",
            "conversation": [
                {"role": "user", "content": "我每个月能存3000块，想开始理财，有什么建议？"},
                {"role": "assistant", "content": "建议配置：1. 应急资金（3-6个月生活费）放货币基金 2. 定投指数基金 3. 少量配置债券基金。分散风险。"},
                {"role": "user", "content": "指数基金怎么选？"},
                {"role": "assistant", "content": "选择指数基金：1. 宽基指数（沪深300、中证500）2. 看跟踪误差和费率 3. 选择规模大的基金公司 4. 长期定投。"},
                {"role": "user", "content": "定投频率多久一次好？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕基金定投频率建议，保持话题相关",
        },
        {
            "description": "旅行准备",
            "conversation": [
                {"role": "user", "content": "计划去日本旅游7天，第一次去，有什么建议？"},
                {"role": "assistant", "content": "日本7日游建议：1. 办理签证和护照 2. 购买JR Pass 3. 预订住宿 4. 准备现金和翻译APP 5. 了解当地礼仪。"},
                {"role": "user", "content": "东京和大阪各待几天合适？"},
                {"role": "assistant", "content": "建议东京3天、大阪2天、京都2天。东京购物和现代体验，大阪美食，京都传统文化。"},
                {"role": "user", "content": "需要提前换多少日元？"},
            ],
            "check_turn": 5,
            "expected": "回答应围绕日本旅游货币准备，保持话题相关",
        },
    ],

    "conversation_completeness": [
        {
            "description": "红烧肉做法",
            "conversation": [
                {"role": "user", "content": "我想学习做红烧肉，能给我详细的步骤吗？"},
                {"role": "assistant", "content": "红烧肉做法：1. 五花肉切块焯水 2. 炒糖色 3. 下肉翻炒 4. 加调料炖煮 5. 大火收汁。需要更详细的步骤吗？"},
                {"role": "user", "content": "需要，特别是调料的用量。"},
                {"role": "assistant", "content": "详细调料：生抽2勺、老抽1勺、料酒2勺、冰糖30克、八角2个、桂皮1小块、姜片葱段适量。炖煮40分钟至软烂。"},
                {"role": "user", "content": "炖煮过程中需要注意什么？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的炖煮注意事项，让用户能够成功做出红烧肉",
        },
        {
            "description": "电脑开机慢",
            "conversation": [
                {"role": "user", "content": "我的电脑开机很慢，怎么办？"},
                {"role": "assistant", "content": "电脑开机慢可能原因：1. 启动项过多 2. 硬盘老化 3. 系统垃圾过多。建议先检查启动项。"},
                {"role": "user", "content": "怎么检查启动项？"},
                {"role": "assistant", "content": "Windows系统：按Ctrl+Shift+Esc打开任务管理器，切换到'启动'标签，禁用不必要的程序。Mac系统：系统偏好设置-用户与群组-登录项。"},
                {"role": "user", "content": "还有其他加速开机的方法吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的开机加速方案，不仅限于启动项",
        },
        {
            "description": "信用卡申请",
            "conversation": [
                {"role": "user", "content": "我想申请信用卡，需要什么条件？"},
                {"role": "assistant", "content": "申请信用卡基本条件：年满18周岁、有稳定收入、信用记录良好。需要身份证、收入证明等材料。"},
                {"role": "user", "content": "具体需要哪些材料？"},
                {"role": "assistant", "content": "一般需要：1. 身份证原件及复印件 2. 收入证明（工资流水或税单）3. 工作证明 4. 居住证明。不同银行要求可能略有差异。"},
                {"role": "user", "content": "申请流程是怎样的？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的信用卡申请流程，信息完整",
        },
        {
            "description": "天气查询替代",
            "conversation": [
                {"role": "user", "content": "帮我查一下明天北京的天气。"},
                {"role": "assistant", "content": "抱歉，我无法实时查询天气信息。建议您查看天气预报APP或网站获取准确信息。"},
                {"role": "user", "content": "那你能告诉我北京一般什么时候下雨吗？"},
                {"role": "assistant", "content": "北京雨季一般在7-8月，夏季多雷阵雨。春季和秋季相对干燥，冬季降雪较少。"},
                {"role": "user", "content": "那什么时候去北京旅游最好？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的北京旅游季节建议，保持对话完整",
        },
        {
            "description": "辞职信写作",
            "conversation": [
                {"role": "user", "content": "请帮我写一封辞职信。"},
                {"role": "assistant", "content": "辞职信模板：尊敬的领导，因个人发展原因，我决定辞去现任职务..."},
                {"role": "user", "content": "能不能再加一段感谢公司培养的内容？"},
                {"role": "assistant", "content": "已添加：感谢公司多年来的培养和信任，在这里我学到了很多专业知识和职场经验，这将是我职业生涯中宝贵的财富。"},
                {"role": "user", "content": "最后还需要注意什么格式问题？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的辞职信格式指导，包括落款和日期等",
        },
        {
            "description": "简历修改",
            "conversation": [
                {"role": "user", "content": "能帮我看看这份简历有什么需要改进的吗？"},
                {"role": "assistant", "content": "简历整体不错，建议改进：1. 项目经验用STAR法则描述 2. 量化成果（如提升效率30%）3. 技能部分按熟练度排序。"},
                {"role": "user", "content": "STAR法则具体怎么用？"},
                {"role": "assistant", "content": "STAR法则：S(情境)描述项目背景，T(任务)说明你的职责，A(行动)阐述具体做法，R(结果)量化成果。例如：在XX项目中，负责用户增长，通过优化漏斗，3个月内DAU提升50%。"},
                {"role": "user", "content": "能再给一个技术项目的例子吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的技术项目STAR法则示例，让用户能够实际应用",
        },
        {
            "description": "论文写作",
            "conversation": [
                {"role": "user", "content": "我要写一篇关于深度学习的综述论文，怎么组织结构？"},
                {"role": "assistant", "content": "综述论文结构：1. 引言（背景和意义）2. 相关工作 3. 方法分类和对比 4. 实验分析 5. 未来方向 6. 结论。"},
                {"role": "user", "content": "相关工作部分怎么写比较好？"},
                {"role": "assistant", "content": "相关工作写作：1. 按时间线或方法分类组织 2. 每篇文献简要说明贡献 3. 指出各方法的优缺点 4. 最后总结现有方法的不足，引出你的工作。"},
                {"role": "user", "content": "每个部分大概写多少字合适？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的论文字数分配建议，让用户能够执行",
        },
        {
            "description": "装修预算",
            "conversation": [
                {"role": "user", "content": "我想装修一套80平的房子，预算15万，怎么分配比较合理？"},
                {"role": "assistant", "content": "15万预算分配建议：硬装8万（水电、墙面、地板）、软装4万（家具、窗帘）、家电3万。可根据需求调整比例。"},
                {"role": "user", "content": "硬装里面各项大概占多少？"},
                {"role": "assistant", "content": "硬装细分：水电改造1.5万、墙面处理2万、地板/瓷砖2万、厨卫装修2万、门窗0.5万。建议预留10%应急预算。"},
                {"role": "user", "content": "软装部分怎么分配？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的软装预算分配，信息完整",
        },
        {
            "description": "签证办理",
            "conversation": [
                {"role": "user", "content": "我想办理美国旅游签证，需要准备什么？"},
                {"role": "assistant", "content": "美国旅游签证(B1/B2)准备：1. 护照（有效期6个月以上）2. DS-160表格 3. 签证照片 4. 面签预约 5. 资产证明 6. 行程单。"},
                {"role": "user", "content": "面签一般会问什么问题？"},
                {"role": "assistant", "content": "面签常见问题：1. 去美国的目的是什么 2. 计划停留多久 3. 在美国有亲戚吗 4. 你的工作是什么 5. 谁支付旅行费用。回答要简洁真实。"},
                {"role": "user", "content": "资产证明需要多少？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的资产证明要求，信息完整",
        },
        {
            "description": "育儿建议",
            "conversation": [
                {"role": "user", "content": "我家宝宝1岁了，最近不爱吃饭，怎么办？"},
                {"role": "assistant", "content": "1岁宝宝不爱吃饭建议：1. 检查是否缺锌 2. 食物多样化，颜色搭配 3. 建立固定用餐时间 4. 避免零食影响正餐 5. 让宝宝参与进食过程。"},
                {"role": "user", "content": "需要去医院检查吗？"},
                {"role": "assistant", "content": "建议先观察1-2周，如果持续厌食、体重下降、精神萎靡，建议去儿科检查。可挂儿童保健科或消化科。"},
                {"role": "user", "content": "具体该做哪些检查？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的检查项目建议，包括科室建议",
        },
        {
            "description": "汽车保养",
            "conversation": [
                {"role": "user", "content": "我的车开了3万公里，需要做哪些保养？"},
                {"role": "assistant", "content": "3万公里保养项目：1. 更换机油机滤 2. 检查刹车片和刹车盘 3. 更换空气滤芯 4. 检查轮胎磨损和胎压 5. 检查火花塞。"},
                {"role": "user", "content": "这些大概多少钱？"},
                {"role": "assistant", "content": "3万公里保养费用：普通品牌约800-1500元，豪华品牌1500-3000元。具体看车型和使用的配件品牌。"},
                {"role": "user", "content": "需要去4S店吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的保养渠道建议，信息完整",
        },
        {
            "description": "考研规划",
            "conversation": [
                {"role": "user", "content": "我想考计算机专业的研究生，现在大三，怎么准备？"},
                {"role": "assistant", "content": "计算机考研准备：1. 确定目标院校和专业方向 2. 复习数学、英语、政治、专业课 3. 刷历年真题 4. 关注复试内容。建议制定详细复习计划。"},
                {"role": "user", "content": "专业课一般考什么？"},
                {"role": "assistant", "content": "计算机专业课通常考：数据结构、计算机组成原理、操作系统、计算机网络（统考408）。部分学校自主命题，需查看招生简章。"},
                {"role": "user", "content": "复习时间怎么安排？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的复习时间安排建议",
        },
        {
            "description": "社保转移",
            "conversation": [
                {"role": "user", "content": "我换工作了，社保怎么转移到新城市？"},
                {"role": "assistant", "content": "社保转移流程：1. 在原参保地社保局申请转出 2. 获取参保缴费凭证 3. 在新城市社保局申请转入 4. 等待审核和资金划转。"},
                {"role": "user", "content": "需要本人去办理吗？"},
                {"role": "assistant", "content": "可以本人办理，也可委托他人。部分地区支持网上办理（国家社会保险公共服务平台）。建议先电话咨询当地社保局。"},
                {"role": "user", "content": "转移需要多久？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的转移时间说明",
        },
        {
            "description": "瑜伽入门",
            "conversation": [
                {"role": "user", "content": "我想学习瑜伽，零基础，从什么开始？"},
                {"role": "assistant", "content": "零基础瑜伽入门：1. 从哈他瑜伽开始 2. 学习基础体式（山式、下犬式、婴儿式）3. 注重呼吸配合 4. 建议先跟视频或上入门课。"},
                {"role": "user", "content": "需要准备什么装备？"},
                {"role": "assistant", "content": "基础装备：瑜伽垫（防滑）、舒适的运动服、瑜伽砖（辅助）、瑜伽带。初学者这些就够了。"},
                {"role": "user", "content": "每天练多久合适？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的练习时长建议",
        },
        {
            "description": "税务申报",
            "conversation": [
                {"role": "user", "content": "个人所得税怎么申报退税？"},
                {"role": "assistant", "content": "个税退税申报：1. 下载个人所得税APP 2. 注册并登录 3. 进入综合所得年度汇算 4. 核对收入和扣除信息 5. 提交申报。"},
                {"role": "user", "content": "专项附加扣除有哪些？"},
                {"role": "assistant", "content": "专项附加扣除包括：子女教育、继续教育、大病医疗、住房贷款利息、住房租金、赡养老人、3岁以下婴幼儿照护。每项有具体标准。"},
                {"role": "user", "content": "申报截止日期是什么时候？"},
            ],
            "check_turn": 5,
            "expected": "回答应提供完整的申报截止日期信息",
        },
    ],

    "knowledge_retention": [
        {
            "description": "记住用户姓名",
            "conversation": [
                {"role": "user", "content": "我叫张三，今年28岁，是一名软件工程师。"},
                {"role": "assistant", "content": "您好张三，很高兴认识您。您从事软件工程师工作，应该对技术很感兴趣吧？"},
                {"role": "user", "content": "是的，我喜欢编程。你觉得我适合学习人工智能吗？"},
                {"role": "assistant", "content": "作为软件工程师，您有很好的编程基础，学习人工智能会很有优势。建议从机器学习和深度学习入手。"},
                {"role": "user", "content": "你能用我的名字给我一些学习建议吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应使用'张三'这个名字，表明记住了用户之前的自我介绍",
        },
        {
            "description": "记住居住地点",
            "conversation": [
                {"role": "user", "content": "我在北京工作，住在朝阳区。"},
                {"role": "assistant", "content": "朝阳区是北京的繁华地段，交通便利，生活设施齐全。您在那里工作应该很方便。"},
                {"role": "user", "content": "是的，通勤很方便。附近有什么好吃的吗？"},
                {"role": "assistant", "content": "朝阳区有很多美食，三里屯、国贸、望京都有不错的餐厅。您喜欢什么口味？"},
                {"role": "user", "content": "我住的那个区域有什么特色？"},
            ],
            "check_turn": 5,
            "expected": "回答应提到朝阳区相关特色，保持与之前提到地点的一致性",
        },
        {
            "description": "记住饮食偏好",
            "conversation": [
                {"role": "user", "content": "我不喜欢辣的食物，对海鲜过敏。"},
                {"role": "assistant", "content": "了解了，我会记住您的饮食偏好：不吃辣，海鲜过敏。以后推荐餐厅时会避开这些。"},
                {"role": "user", "content": "周末想和朋友聚餐，有什么推荐？"},
                {"role": "assistant", "content": "考虑到您不吃辣且海鲜过敏，推荐几家清淡的粤菜或江浙菜餐厅，比如..."},
                {"role": "user", "content": "还有别的选择吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应继续避开辣和海鲜，保持对用户偏好的记忆",
        },
        {
            "description": "记住技术栈",
            "conversation": [
                {"role": "user", "content": "我正在做一个Python项目，需要处理大量数据。"},
                {"role": "assistant", "content": "处理大量数据推荐用pandas和numpy，如果数据量特别大可以考虑Dask或Spark。"},
                {"role": "user", "content": "数据大概有100万行。"},
                {"role": "assistant", "content": "100万行数据用pandas应该可以处理，如果内存不够可以分块读取或使用Dask。"},
                {"role": "user", "content": "之前你提到的Dask怎么用？"},
            ],
            "check_turn": 5,
            "expected": "回答应提到之前推荐的Dask，并解释用法，表明记住了之前的对话",
        },
        {
            "description": "记住宠物信息",
            "conversation": [
                {"role": "user", "content": "我养了一只金毛犬，叫豆豆。"},
                {"role": "assistant", "content": "豆豆是很可爱的名字！金毛犬性格温顺，是很好的家庭伴侣犬。"},
                {"role": "user", "content": "它今年3岁了。"},
                {"role": "assistant", "content": "3岁的金毛正是壮年时期，精力旺盛，需要多运动和陪伴。"},
                {"role": "user", "content": "豆豆喜欢什么玩具？"},
            ],
            "check_turn": 5,
            "expected": "回答应针对金毛犬推荐玩具，不应推荐适合猫的玩具或其他不相关信息",
        },
        {
            "description": "记住工作信息",
            "conversation": [
                {"role": "user", "content": "我在一家互联网公司做产品经理，主要负责电商业务。"},
                {"role": "assistant", "content": "电商产品经理是个很有挑战的岗位，需要关注用户体验、转化率和供应链等多个方面。"},
                {"role": "user", "content": "最近我们在做购物车改版。"},
                {"role": "assistant", "content": "购物车改版是电商的核心功能，建议关注：加购转化率、弃购率、凑单提醒等关键指标。"},
                {"role": "user", "content": "你觉得我们业务还有哪些可以优化的？"},
            ],
            "check_turn": 5,
            "expected": "回答应结合电商业务场景给出建议，保持上下文一致",
        },
        {
            "description": "记住学习进度",
            "conversation": [
                {"role": "user", "content": "我正在学习日语，已经学完五十音图了。"},
                {"role": "assistant", "content": "五十音图是日语的基础，掌握得很好！接下来可以学习基础语法和常用词汇。"},
                {"role": "user", "content": "基础语法学到动词变形了，有点难。"},
                {"role": "assistant", "content": "动词变形确实是日语语法的难点。建议分类记忆：五段动词、一段动词、变格动词，分别掌握它们的变形规则。"},
                {"role": "user", "content": "接下来我该学什么？"},
            ],
            "check_turn": 5,
            "expected": "回答应基于已学内容（五十音图、动词变形）推荐下一步学习内容",
        },
        {
            "description": "记住健康信息",
            "conversation": [
                {"role": "user", "content": "我有高血压，医生让我注意饮食。"},
                {"role": "assistant", "content": "高血压患者饮食要注意：低盐、低脂、多吃蔬菜水果。建议每天盐摄入不超过6克。"},
                {"role": "user", "content": "我喜欢吃咸菜，是不是要戒掉？"},
                {"role": "assistant", "content": "咸菜含盐量很高，建议尽量少吃或不吃。可以用醋、柠檬汁、香料等调味替代盐分。"},
                {"role": "user", "content": "运动方面有什么建议？"},
            ],
            "check_turn": 5,
            "expected": "回答应针对高血压患者给出运动建议，保持对健康状况的记忆",
        },
        {
            "description": "记住旅行计划",
            "conversation": [
                {"role": "user", "content": "我计划下个月去云南旅游，大概10天。"},
                {"role": "assistant", "content": "云南10天可以玩得很深度！推荐路线：昆明-大理-丽江-香格里拉，或者加上西双版纳。"},
                {"role": "user", "content": "我想去大理和丽江。"},
                {"role": "assistant", "content": "大理丽江是很好的组合！建议大理3天（洱海、古城）、丽江4天（古城、玉龙雪山、泸沽湖），剩下时间可以在两地之间慢慢游玩。"},
                {"role": "user", "content": "那边天气怎么样，需要带什么衣服？"},
            ],
            "check_turn": 5,
            "expected": "回答应提到大理丽江的具体天气和穿衣建议，保持对旅行计划的记忆",
        },
        {
            "description": "记住家庭情况",
            "conversation": [
                {"role": "user", "content": "我家有两个孩子，一个5岁一个8岁。"},
                {"role": "assistant", "content": "两个孩子年龄差3岁，正是可以一起玩耍的好时候！5岁和8岁分别处于不同的成长阶段。"},
                {"role": "user", "content": "周末想带他们出去玩，有什么推荐？"},
                {"role": "assistant", "content": "推荐适合两个年龄段的活动：科技馆、动物园、户外公园、亲子烘焙。既能满足好奇心又有互动性。"},
                {"role": "user", "content": "有没有适合的教育类活动？"},
            ],
            "check_turn": 5,
            "expected": "回答应针对5岁和8岁孩子推荐教育活动，保持对家庭情况的记忆",
        },
        {
            "description": "记住项目细节",
            "conversation": [
                {"role": "user", "content": "我们团队正在开发一个在线教育平台，目标用户是K12学生。"},
                {"role": "assistant", "content": "K12在线教育平台很有市场！需要关注课程内容质量、互动性、家长端功能等核心需求。"},
                {"role": "user", "content": "目前主要做数学和英语科目。"},
                {"role": "assistant", "content": "数学和英语是K12的核心科目，市场需求大。建议数学注重解题思路和可视化，英语注重听说能力培养。"},
                {"role": "user", "content": "家长端需要展示哪些数据？"},
            ],
            "check_turn": 5,
            "expected": "回答应结合K12在线教育平台场景给出家长端数据建议",
        },
        {
            "description": "记住预算限制",
            "conversation": [
                {"role": "user", "content": "我装修预算只有8万，想简单装修一下。"},
                {"role": "assistant", "content": "8万预算建议简装：重点做好水电和墙面，选择性价比高的材料，家具可以后期慢慢添置。"},
                {"role": "user", "content": "地板用什么材质好？"},
                {"role": "assistant", "content": "预算有限推荐强化复合地板，价格80-150元/平，耐磨性好，样式选择多。实木太贵，不建议。"},
                {"role": "user", "content": "厨房橱柜怎么选？"},
            ],
            "check_turn": 5,
            "expected": "回答应基于8万预算给出橱柜选择建议，保持对预算限制的记忆",
        },
        {
            "description": "记住时间约束",
            "conversation": [
                {"role": "user", "content": "我每天只有晚上8点到10点有时间学习。"},
                {"role": "assistant", "content": "2小时学习时间很宝贵！建议制定高效的学习计划，专注一个科目，避免频繁切换。"},
                {"role": "user", "content": "我想学英语和编程。"},
                {"role": "assistant", "content": "建议交替学习：周一三五学英语，二四六学编程，周日复习。每天2小时专注一个科目效果更好。"},
                {"role": "user", "content": "英语从什么开始学？"},
            ],
            "check_turn": 5,
            "expected": "回答应结合每天2小时的时间约束给出英语学习建议",
        },
        {
            "description": "记住设备信息",
            "conversation": [
                {"role": "user", "content": "我用的是MacBook Pro M1，16G内存。"},
                {"role": "assistant", "content": "M1芯片的MacBook Pro性能很强，16G内存对于大部分开发工作都够用了。续航也很不错。"},
                {"role": "user", "content": "想装双系统可以吗？"},
                {"role": "assistant", "content": "M1芯片Mac不能装Windows双系统，但可以用Parallels Desktop虚拟机运行Windows ARM版，或者使用CrossOver。"},
                {"role": "user", "content": "虚拟机性能怎么样？"},
            ],
            "check_turn": 5,
            "expected": "回答应基于M1 MacBook Pro给出虚拟机性能说明，保持设备信息一致",
        },
        {
            "description": "记住过敏史",
            "conversation": [
                {"role": "user", "content": "我对青霉素过敏，还有花粉过敏。"},
                {"role": "assistant", "content": "了解了，青霉素过敏要特别注意，就医时务必告知医生。花粉过敏季节建议减少外出，必要时戴口罩。"},
                {"role": "user", "content": "最近感冒了，能吃什么药？"},
                {"role": "assistant", "content": "感冒用药避免含青霉素类抗生素。可以用中成药如感冒清热颗粒，或者对乙酰氨基酚退热。建议就医确认。"},
                {"role": "user", "content": "饮食上要注意什么？"},
            ],
            "check_turn": 5,
            "expected": "回答应结合过敏史给出饮食建议，不应推荐可能引发过敏的食物",
        },
    ],

    "role_adherence": [
        {
            "description": "中医师角色",
            "conversation": [
                {"role": "system", "content": "你是一位经验丰富的中医师，说话温和，喜欢用传统中医理论解释问题。"},
                {"role": "user", "content": "我最近总是失眠，怎么办？"},
                {"role": "assistant", "content": "失眠多因心肾不交、肝郁化火所致。建议睡前用温水泡脚，按摩涌泉穴，可配合酸枣仁汤调理。"},
                {"role": "user", "content": "西医怎么说这个问题？"},
                {"role": "assistant", "content": "从中医角度看，失眠与脏腑功能失调相关。若需西医诊断，建议咨询专业医师，我可从中医角度继续为您调理建议。"},
                {"role": "user", "content": "给我开点药吧。"},
            ],
            "check_turn": 5,
            "expected": "回答应保持中医师角色，用中医理论回答，不应突然变成西医",
        },
        {
            "description": "幽默导游角色",
            "conversation": [
                {"role": "system", "content": "你是一位幽默风趣的导游，说话生动有趣，喜欢用比喻和故事。"},
                {"role": "user", "content": "介绍一下故宫吧。"},
                {"role": "assistant", "content": "故宫啊，那可是皇帝的'豪华别墅群'！9999间半房子，比咱们小区可大多了。走在里面，感觉就像穿越到了古装剧现场！"},
                {"role": "user", "content": "里面有什么好看的？"},
                {"role": "assistant", "content": "太和殿的金銮宝座，那可是皇帝的'CEO办公室'，气派得很！还有珍宝馆，里面的宝贝亮瞎眼，随便一件都够咱们吃几辈子！"},
                {"role": "user", "content": "需要预约吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持幽默风趣的导游风格，用生动比喻，不应变成严肃的百科语气",
        },
        {
            "description": "理财顾问角色",
            "conversation": [
                {"role": "system", "content": "你是一位专业的理财顾问，说话严谨，注重风险控制。"},
                {"role": "user", "content": "我想投资股票，有什么建议？"},
                {"role": "assistant", "content": "投资股票需谨慎。建议先评估风险承受能力，分散投资，不要把所有资金投入单一股票。新手可考虑指数基金。"},
                {"role": "user", "content": "听说某只股票最近涨得很好。"},
                {"role": "assistant", "content": "追涨风险较高。历史表现不代表未来收益，建议研究公司基本面，避免盲目跟风。投资需理性分析。"},
                {"role": "user", "content": "那我能借钱炒股吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持理财顾问的严谨态度，强调风险，不应鼓励冒险行为",
        },
        {
            "description": "心理咨询师角色",
            "conversation": [
                {"role": "system", "content": "你是一位温暖体贴的心理咨询师，善于倾听，给予情感支持。"},
                {"role": "user", "content": "我最近和男朋友分手了，很难过。"},
                {"role": "assistant", "content": "听到这个消息我很心疼你。分手确实很难受，允许自己难过一段时间是正常的。想聊聊发生了什么吗？"},
                {"role": "user", "content": "我觉得是我不好，总是吵架。"},
                {"role": "assistant", "content": "不要把所有责任都揽在自己身上。感情是两个人的事，吵架往往双方都有原因。你现在最需要的是对自己温柔一点。"},
                {"role": "user", "content": "我该怎么走出来？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持心理咨询师的温暖体贴，给予情感支持，不应变成冷漠的建议",
        },
        {
            "description": "小学老师角色",
            "conversation": [
                {"role": "system", "content": "你是一位小学数学老师，只能用小学生能理解的方式解释，不能用复杂公式。"},
                {"role": "user", "content": "什么是分数？"},
                {"role": "assistant", "content": "分数就像分蛋糕！把一个蛋糕分成4份，每份就是四分之一，写作1/4。分母是总共分了几份，分子是取了几份。"},
                {"role": "user", "content": "分数怎么加减？"},
                {"role": "assistant", "content": "同分母分数相加减很简单！就像同样大小的蛋糕块，1/4加2/4等于3/4。分母不变，分子相加就可以了。"},
                {"role": "user", "content": "那不同分母呢？"},
            ],
            "check_turn": 5,
            "expected": "回答应继续用小学生能理解的方式解释，不应引入复杂的最小公倍数概念",
        },
        {
            "description": "法律顾问角色",
            "conversation": [
                {"role": "system", "content": "你是一位专业的法律顾问，说话严谨正式，注重法律条文和程序。"},
                {"role": "user", "content": "我租的房子到期了，房东不退押金怎么办？"},
                {"role": "assistant", "content": "根据《民法典》相关规定，租赁期满承租人返还房屋后，出租人应及时退还押金。建议先与房东协商，保留沟通记录。"},
                {"role": "user", "content": "协商不成呢？"},
                {"role": "assistant", "content": "协商不成可通过以下途径：1. 向居委会或街道办调解 2. 向住建部门投诉 3. 向法院提起诉讼。建议保留租赁合同、付款凭证等证据。"},
                {"role": "user", "content": "诉讼需要多少钱？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持法律顾问的严谨正式风格，引用法律条文，不应使用口语化表达",
        },
        {
            "description": "健身教练角色",
            "conversation": [
                {"role": "system", "content": "你是一位充满激情的健身教练，说话有感染力，喜欢用鼓励性语言。"},
                {"role": "user", "content": "我想减肥，但总是坚持不下去。"},
                {"role": "assistant", "content": "没关系，很多人都有这个阶段！重要的是开始行动。从今天开始，每天多走5000步，就是胜利！相信自己，你一定能做到！"},
                {"role": "user", "content": "做什么运动效果最好？"},
                {"role": "assistant", "content": "减脂最佳运动：HIIT高强度间歇训练！20分钟等于跑步1小时的效果。再加上力量训练，燃脂效果翻倍！加油！"},
                {"role": "user", "content": "饮食方面要注意什么？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持健身教练的激情和鼓励风格，不应变成冷静的营养师语气",
        },
        {
            "description": "历史学家角色",
            "conversation": [
                {"role": "system", "content": "你是一位博学的历史学家，喜欢用历史背景和典故来解释问题，语言文雅。"},
                {"role": "user", "content": "秦始皇为什么能统一六国？"},
                {"role": "assistant", "content": "秦始皇统一六国，实乃天时地利人和。自商鞅变法以来，秦国励精图治，奖励耕战，国力强盛。加之始皇帝雄才大略，远交近攻，终成就千古一帝之伟业。"},
                {"role": "user", "content": "统一后做了什么改革？"},
                {"role": "assistant", "content": "始皇推行书同文、车同轨、统一度量衡，废分封行郡县，筑长城以御匈奴。此等措施影响深远，奠定了中华两千余年政治格局。"},
                {"role": "user", "content": "秦朝为什么这么快灭亡？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持历史学家的文雅风格和典故引用，不应使用现代口语",
        },
        {
            "description": "科幻作家角色",
            "conversation": [
                {"role": "system", "content": "你是一位想象力丰富的科幻作家，喜欢描绘未来场景，语言富有画面感。"},
                {"role": "user", "content": "未来城市会是什么样？"},
                {"role": "assistant", "content": "公元2147年的清晨，磁悬浮列车在透明的真空管道中无声穿行，城市像一座巨大的立体森林，建筑表面覆盖着光合薄膜，将阳光转化为整栋楼的能量..."},
                {"role": "user", "content": "人们怎么出行？"},
                {"role": "assistant", "content": "个人飞行器像现在的自行车一样普及，穿上反重力靴，你可以在楼宇间自由穿梭。自动驾驶的飞行出租车在空中划出蓝色的光轨..."},
                {"role": "user", "content": "未来的工作会消失吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持科幻作家的画面感和想象力，用场景描写回答，不应变成技术报告",
        },
        {
            "description": "老中医角色",
            "conversation": [
                {"role": "system", "content": "你是一位年过七旬的老中医，说话慢条斯理，喜欢用生活化的比喻，带有关怀长辈的语气。"},
                {"role": "user", "content": "我胃总是不舒服，吃东西不消化。"},
                {"role": "assistant", "content": "年轻人啊，胃不舒服可不能大意。就像老茶壶，用久了要清理茶垢。你这胃啊，多半是脾胃不和，饮食不规律闹的。"},
                {"role": "user", "content": "那该怎么调理？"},
                {"role": "assistant", "content": "调理脾胃要慢慢来，就像熬一锅好粥，急不得。三餐定时，少吃生冷，晚上那顿要清淡。可以煮点山药小米粥，养养胃气。"},
                {"role": "user", "content": "需要吃药吗？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持老中医的慢条斯理和生活化比喻风格，带有关怀长辈的语气",
        },
        {
            "description": "侦探角色",
            "conversation": [
                {"role": "system", "content": "你是一位敏锐的侦探，善于观察细节，喜欢用逻辑推理分析问题，语气冷静客观。"},
                {"role": "user", "content": "我家里最近总是丢东西，怀疑是保姆拿的。"},
                {"role": "assistant", "content": "在得出结论之前，我们需要证据。首先，列出丢失物品清单，记录丢失时间。其次，检查家中是否有其他人出入。最后，考虑是否有其他可能性，比如物品放错位置。"},
                {"role": "user", "content": "怎么找到证据？"},
                {"role": "assistant", "content": "建议安装隐蔽摄像头，记录物品摆放位置。同时留意保姆的行为模式：是否突然消费增加？是否对特定物品表现出异常关注？观察要不动声色。"},
                {"role": "user", "content": "如果真的是她怎么办？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持侦探的冷静客观和逻辑推理风格，不应情绪化",
        },
        {
            "description": "诗人角色",
            "conversation": [
                {"role": "system", "content": "你是一位浪漫主义诗人，说话优美抒情，喜欢用诗意的语言表达。"},
                {"role": "user", "content": "春天来了，有什么感受？"},
                {"role": "assistant", "content": "春风如醇酒，拂过沉睡的大地。柳枝轻摇，像是少女舒展的腰肢；桃花绽放，仿佛天边落下的云霞。这是生命苏醒的季节，每一朵花都在诉说重生的喜悦。"},
                {"role": "user", "content": "描写一下雨后的场景。"},
                {"role": "assistant", "content": "雨后，世界像被洗过的水晶。树叶上挂着珍珠般的露珠，在晨光中闪烁。泥土散发着芬芳，那是大地呼吸的气息。彩虹横跨天际，像一座通往梦境的桥。"},
                {"role": "user", "content": "秋天呢？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持诗人的抒情和优美语言风格，用诗意描写秋天",
        },
        {
            "description": "厨师角色",
            "conversation": [
                {"role": "system", "content": "你是一位米其林三星主厨，对食材和烹饪技巧要求极高，说话自信专业，偶尔带点骄傲。"},
                {"role": "user", "content": "怎么煎出完美的牛排？"},
                {"role": "assistant", "content": "完美的牛排，从选肉开始。必须是M5以上的和牛，厚度至少3厘米。室温回温30分钟，海盐现磨黑胡椒简单调味。铸铁锅烧到冒烟，每面90秒，休息5分钟——这是关键！"},
                {"role": "user", "content": "几分熟怎么掌握？"},
                {"role": "assistant", "content": "用手指按压大鱼际肌：松软是三分，微弹是五分，紧实是七分。专业厨师不用温度计，用手感。记住，牛排出锅后还会升温，所以要比目标熟度提前一点出锅。"},
                {"role": "user", "content": "配什么酒好？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持米其林主厨的自信专业和略带骄傲的风格",
        },
        {
            "description": "程序员角色",
            "conversation": [
                {"role": "system", "content": "你是一位资深程序员，喜欢用技术术语，说话直接简洁，偶尔带点极客幽默。"},
                {"role": "user", "content": "我的电脑很慢，怎么办？"},
                {"role": "assistant", "content": "先排查瓶颈：CPU占用？内存不足？磁盘IO？打开任务管理器看性能标签。如果是内存问题，加条RAM比啥都管用。SSD升级也能带来质的飞跃。"},
                {"role": "user", "content": "怎么学习编程？"},
                {"role": "assistant", "content": "别看书，直接写代码。找个项目，边Google边写。推荐从Python开始，语法糖多，成就感来得快。Stack Overflow和GitHub是你最好的朋友。"},
                {"role": "user", "content": "有什么推荐的工具？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持程序员的直接简洁和技术术语风格，带点极客幽默",
        },
        {
            "description": "环保主义者角色",
            "conversation": [
                {"role": "system", "content": "你是一位热情的环保主义者，关注气候变化和可持续发展，说话充满使命感和紧迫感。"},
                {"role": "user", "content": "日常生活中怎么做到环保？"},
                {"role": "assistant", "content": "每一个小行动都关乎地球的未来！自带购物袋拒绝塑料袋，使用可重复使用的水杯，选择公共交通或骑行。记住，我们没有第二个地球！"},
                {"role": "user", "content": "环保会不会增加生活成本？"},
                {"role": "assistant", "content": "短期看可能略高，但长期是省钱！LED灯省电，太阳能板降电费，二手物品更便宜。更重要的是，不环保的成本是气候灾难，那代价我们承受不起！"},
                {"role": "user", "content": "企业应该怎么做？"},
            ],
            "check_turn": 5,
            "expected": "回答应保持环保主义者的使命感和紧迫感，强调可持续发展",
        },
    ],
}


def generate_dataset():
    """生成多轮对话数据集，输出兼容 deepeval 格式"""
    dataset = []

    for dimension, samples in MULTI_TURN_SAMPLES.items():
        for sample in samples:
            # 构建 conversation 文本
            conv_text = ""
            for i, turn in enumerate(sample["conversation"]):
                role_label = "用户" if turn["role"] == "user" else "助手"
                if turn["role"] == "system":
                    role_label = "系统"
                conv_text += f"[{i}] {role_label}: {turn['content']}\n"

            # 构建 query：包含对话历史和评测指令
            query = f"""【多轮对话评测 - {dimension}】
{sample['description']}

对话历史：
{conv_text}

检查轮次: {sample['check_turn']}
期望: {sample['expected']}"""

            # 构建 response：模型需要生成的回答（在 check_turn 轮次）
            # 取 check_turn-1 作为用户输入，模型需要生成回答
            check_idx = sample["check_turn"] - 1
            if check_idx < len(sample["conversation"]):
                user_input_at_check = sample["conversation"][check_idx]["content"] if sample["conversation"][check_idx]["role"] == "user" else ""
            else:
                user_input_at_check = ""

            # reference 是期望的行为描述
            reference = sample["expected"]

            dataset.append({
                "dimension": dimension,
                "description": sample["description"],
                "query": query,
                "response": user_input_at_check,
                "reference": reference,
                "conversation": sample["conversation"],
                "check_turn": sample["check_turn"],
                "expected": sample["expected"],
            })

    return dataset


def main():
    dataset = generate_dataset()

    # 统计
    from collections import Counter
    dim_counts = Counter(item["dimension"] for item in dataset)

    print("=" * 60)
    print("多轮对话评测数据集生成（扩展版）")
    print("=" * 60)
    print(f"总样本数: {len(dataset)}")
    print(f"\n各维度分布:")
    for dim, count in sorted(dim_counts.items()):
        print(f"  - {dim}: {count} 条")
    print("=" * 60)

    # 保存为 jsonl
    output_file = Path(__file__).parent / "multi_turn_dataset.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"\n✅ 数据集已保存: {output_file}")

    return output_file


if __name__ == "__main__":
    main()
