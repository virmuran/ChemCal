# ChemCal/modules/countdowns.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QPushButton, QScrollArea, QGridLayout, QFrame,
                               QMessageBox, QInputDialog, QGroupBox, QSpinBox)
from PySide6.QtCore import Qt, QTimer, QDateTime, QSize
from PySide6.QtGui import QFont, QPalette, QColor
from datetime import datetime, timedelta

class CountdownsWidget(QWidget):
    """倒计时模块 - 动态列数版"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.active_countdowns = {}
        self.selected_countdown_id = None
        self.countdown_cards = {}  # 存储倒计时卡片的引用
        
        self.setup_ui()
        self.refresh_countdowns()
        self.start_datetime_updater()
        self.auto_start_countdowns()  # 自动开始未完成的倒计时
    
    def setup_ui(self):
        """设置倒计时UI - 只保留日期倒计时"""
        main_layout = QVBoxLayout(self)
        
        # 当前日期和时间显示
        datetime_frame = QWidget()
        datetime_layout = QHBoxLayout(datetime_frame)
        
        self.current_date_label = QLabel("正在加载...")
        self.current_date_label.setFont(QFont("Arial", 10))
        datetime_layout.addWidget(self.current_date_label)
        
        self.current_time_label = QLabel("正在加载...")
        self.current_time_label.setFont(QFont("Arial", 10, QFont.Bold))
        datetime_layout.addWidget(self.current_time_label)
        
        datetime_layout.addStretch()
        main_layout.addWidget(datetime_frame)
        
        # 添加日期倒计时框架
        add_group = QGroupBox("添加日期倒计时")
        main_layout.addWidget(add_group)
        
        add_layout = QVBoxLayout(add_group)
        
        # 事件名称输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("事件名称:"))
        self.name_entry = QLineEdit()
        name_layout.addWidget(self.name_entry)
        add_layout.addLayout(name_layout)
        
        # 日期输入框架
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("目标日期:"))
        self.target_date_entry = QLineEdit()
        self.target_date_entry.setFixedWidth(100)
        date_layout.addWidget(self.target_date_entry)
        date_layout.addWidget(QLabel("(YYYY-MM-DD)"))
        date_layout.addStretch()
        add_layout.addLayout(date_layout)
        
        # 时间选择框架
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("目标时间:"))
        
        self.hour_spinbox = QSpinBox()
        self.hour_spinbox.setRange(0, 23)
        self.hour_spinbox.setValue(0)
        self.hour_spinbox.setFixedWidth(50)
        time_layout.addWidget(self.hour_spinbox)
        time_layout.addWidget(QLabel("时"))
        
        self.minute_spinbox = QSpinBox()
        self.minute_spinbox.setRange(0, 59)
        self.minute_spinbox.setValue(0)
        self.minute_spinbox.setFixedWidth(50)
        time_layout.addWidget(self.minute_spinbox)
        time_layout.addWidget(QLabel("分"))
        
        time_layout.addStretch()
        add_layout.addLayout(time_layout)
        
        # 添加按钮
        add_btn = QPushButton("添加倒计时")
        add_btn.clicked.connect(self.add_countdown)
        add_layout.addWidget(add_btn)
        
        # 倒计时列表框架
        list_group = QGroupBox("倒计时列表")
        main_layout.addWidget(list_group)
        
        list_layout = QVBoxLayout(list_group)
        
        # 使用QScrollArea实现可滚动的倒计时列表
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QGridLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        list_layout.addWidget(self.scroll_area)
        
        # 按钮框架
        button_layout = QHBoxLayout()
        
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_countdown)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_countdown)
        button_layout.addWidget(delete_btn)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_countdowns)
        button_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("清空所有")
        clear_btn.clicked.connect(self.clear_all_countdowns)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        list_layout.addLayout(button_layout)
        
        # 状态显示
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Arial", 9))
        list_layout.addWidget(self.status_label)
        
        # 设置定时器更新倒计时显示
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.refresh_countdowns)
        self.countdown_timer.start(1000)  # 每秒更新一次
    
    def auto_start_countdowns(self):
        """自动开始所有未完成的倒计时 - 精确到秒"""
        countdowns = self.data_manager.get_countdowns()
        auto_started = 0
        
        for countdown in countdowns:
            countdown_id_str = str(countdown["id"])
            
            # 如果已经在活动列表中，跳过
            if countdown_id_str in self.active_countdowns:
                continue
                
            # 检查倒计时是否已完成或过期
            target_time_str = countdown.get("target_time", "23:59:00")  # 默认包含秒数
            
            # 尝试不同的时间格式
            try:
                # 先尝试包含秒数的格式
                target_datetime = datetime.strptime(
                    f"{countdown['target_date']} {target_time_str}", 
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                try:
                    # 如果不包含秒数，使用默认格式并添加秒数
                    target_datetime = datetime.strptime(
                        f"{countdown['target_date']} {target_time_str}", 
                        "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    # 如果还是失败，使用默认时间
                    target_datetime = datetime.strptime(
                        f"{countdown['target_date']} 23:59:00", 
                        "%Y-%m-%d %H:%M:%S"
                    )
            
            now = datetime.now()
            if target_datetime <= now:
                continue  # 跳过已过期的倒计时
                
            # 自动开始倒计时
            self.active_countdowns[countdown_id_str] = {
                "running": True,
                "target": target_datetime
            }
            
            auto_started += 1
        
        if auto_started > 0:
            self.status_label.setText(f"已自动开始 {auto_started} 个倒计时")
            QTimer.singleShot(3000, lambda: self.status_label.setText(""))
            self.refresh_countdowns()
    
    def update_datetime(self):
        """更新当前日期和时间显示"""
        now = QDateTime.currentDateTime()
        
        # 更新日期显示
        date_str = now.toString("yyyy年MM月dd日 dddd")
        self.current_date_label.setText(f"当前日期: {date_str}")
        
        # 更新时间显示
        time_str = now.toString("HH:mm:ss")
        self.current_time_label.setText(f"当前时间: {time_str}")
    
    def start_datetime_updater(self):
        """启动日期时间更新器"""
        self.datetime_timer = QTimer()
        self.datetime_timer.timeout.connect(self.update_datetime)
        self.datetime_timer.start(1000)  # 每秒更新一次
        self.update_datetime()  # 立即更新一次
    
    def add_countdown(self):
        """添加倒计时 - 精确到秒"""
        name = self.name_entry.text().strip()
        target_date_str = self.target_date_entry.text().strip()
        
        if not name:
            QMessageBox.critical(self, "错误", "请输入事件名称")
            return
        
        if not target_date_str:
            QMessageBox.critical(self, "错误", "请输入目标日期")
            return
        
        try:
            # 获取时间
            hour = self.hour_spinbox.value()
            minute = self.minute_spinbox.value()
            second = 0  # 默认秒数为0
            
            # 创建目标日期时间对象
            target_datetime = datetime.strptime(f"{target_date_str} {hour:02d}:{minute:02d}:{second:02d}", "%Y-%m-%d %H:%M:%S")
            
            # 验证日期时间是否有效
            if target_datetime <= datetime.now():
                QMessageBox.critical(self, "错误", "目标时间必须是未来时间")
                return
            
            # 格式化为字符串存储（包含秒数）
            target_time_str = target_datetime.strftime("%H:%M:%S")
            
            self.data_manager.add_countdown(name, target_date_str, target_time_str)
            
            # 清空输入框
            self.name_entry.clear()
            self.target_date_entry.clear()
            
            self.refresh_countdowns()
            self.status_label.setText(f"已添加倒计时: {name}")
            QTimer.singleShot(3000, lambda: self.status_label.setText(""))
            
        except ValueError as e:
            QMessageBox.critical(self, "错误", f"日期或时间格式错误: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")
    
    def edit_countdown(self):
        """编辑倒计时 - 精确到秒"""
        if not self.selected_countdown_id:
            QMessageBox.warning(self, "警告", "请先选择一个倒计时")
            return
        
        countdowns = self.data_manager.get_countdowns()
        countdown = next((c for c in countdowns if c["id"] == self.selected_countdown_id), None)
        
        if not countdown:
            QMessageBox.warning(self, "警告", "选择的倒计时不存在")
            return
        
        # 解析当前时间
        current_time_str = countdown.get("target_time", "23:59:00")
        try:
            current_time = datetime.strptime(current_time_str, "%H:%M:%S")
        except ValueError:
            try:
                current_time = datetime.strptime(current_time_str, "%H:%M")
            except ValueError:
                current_time = datetime.strptime("23:59:00", "%H:%M:%S")
        
        # 弹出编辑对话框
        new_name, ok = QInputDialog.getText(self, "编辑倒计时", "请输入新事件名称:", text=countdown["name"])
        if not ok:  # 用户取消
            return
        
        new_date, ok = QInputDialog.getText(self, "编辑倒计时", "请输入新目标日期 (YYYY-MM-DD):", 
                                          text=countdown["target_date"])
        if not ok:  # 用户取消
            return
        
        # 提供当前时间作为默认值
        default_time = current_time.strftime("%H:%M")
        new_time, ok = QInputDialog.getText(self, "编辑倒计时", "请输入新目标时间 (HH:MM):", 
                                          text=default_time)
        if not ok:  # 用户取消
            return
        
        # 验证日期格式
        try:
            # 添加秒数
            if ":" in new_time and new_time.count(":") == 1:
                new_time += ":00"  # 添加秒数
            
            target_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M:%S")
            if target_datetime <= datetime.now():
                QMessageBox.critical(self, "错误", "目标时间必须是未来时间")
                return
        except ValueError:
            QMessageBox.critical(self, "错误", "日期或时间格式错误，请使用 YYYY-MM-DD 和 HH:MM 格式")
            return
        
        # 停止当前的倒计时
        countdown_id_str = str(countdown["id"])
        if countdown_id_str in self.active_countdowns:
            self.active_countdowns[countdown_id_str]["running"] = False
        
        self.data_manager.update_countdown(countdown["id"], name=new_name, 
                                        target_date=new_date, target_time=new_time)
        self.refresh_countdowns()
        self.status_label.setText(f"已更新倒计时: {new_name}")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))
    
    def delete_countdown(self):
        """删除倒计时"""
        if not self.selected_countdown_id:
            QMessageBox.warning(self, "警告", "请先选择一个倒计时")
            return
        
        countdowns = self.data_manager.get_countdowns()
        countdown = next((c for c in countdowns if c["id"] == self.selected_countdown_id), None)
        
        if not countdown:
            QMessageBox.warning(self, "警告", "选择的倒计时不存在")
            return
        
        # 停止倒计时
        countdown_id_str = str(countdown["id"])
        if countdown_id_str in self.active_countdowns:
            self.active_countdowns[countdown_id_str]["running"] = False
        
        reply = QMessageBox.question(self, "确认", f"确定要删除倒计时 '{countdown['name']}' 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.data_manager.delete_countdown(countdown["id"])
            self.selected_countdown_id = None
            self.refresh_countdowns()
            self.status_label.setText(f"已删除倒计时: {countdown['name']}")
            QTimer.singleShot(3000, lambda: self.status_label.setText(""))
    
    def clear_all_countdowns(self):
        """清空所有倒计时"""
        countdowns = self.data_manager.get_countdowns()
        if not countdowns:
            QMessageBox.information(self, "信息", "倒计时列表已为空")
            return
        
        reply = QMessageBox.question(self, "确认", f"确定要清空所有 {len(countdowns)} 个倒计时吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 停止所有活动倒计时
            for countdown_id in list(self.active_countdowns.keys()):
                self.active_countdowns[countdown_id]["running"] = False
            
            # 删除所有倒计时
            for countdown in countdowns:
                self.data_manager.delete_countdown(countdown["id"])
            
            self.selected_countdown_id = None
            self.refresh_countdowns()
            self.status_label.setText("已清空所有倒计时")
            QTimer.singleShot(3000, lambda: self.status_label.setText(""))
    
    def select_countdown(self, countdown_id):
        """选择倒计时"""
        self.selected_countdown_id = countdown_id
        self.refresh_countdowns()  # 刷新显示以突出显示选中的倒计时
    
    def check_countdown_finished(self, countdown_id, countdown):
        """检查倒计时是否结束"""
        countdown_id_str = str(countdown_id)
        if countdown_id_str in self.active_countdowns:
            target_datetime = self.active_countdowns[countdown_id_str]["target"]
            now = datetime.now()
            
            if now >= target_datetime:
                # 倒计时结束
                self.countdown_finished(countdown_id, countdown)
                return True
        return False
    
    def countdown_finished(self, countdown_id, countdown):
        """倒计时结束处理"""
        # 显示通知
        QMessageBox.information(self, "倒计时结束", f"'{countdown['name']}' 的时间到了！")
        
        # 从活动倒计时中移除
        countdown_id_str = str(countdown_id)
        if countdown_id_str in self.active_countdowns:
            del self.active_countdowns[countdown_id_str]
        
        # 刷新显示
        self.refresh_countdowns()
    
    def refresh_countdowns(self):
        """刷新倒计时列表 - 动态列数布局，精确到秒"""
        countdowns = self.data_manager.get_countdowns()
        
        # 清除现有显示
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.countdown_cards = {}
        
        if not countdowns:
            no_countdowns_label = QLabel("暂无倒计时，请在上方添加新倒计时")
            no_countdowns_label.setFont(QFont("Arial", 12))
            no_countdowns_label.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(no_countdowns_label, 0, 0)
            return
        
        # 计算每行可以放置的列数
        # 增加卡片宽度以适应较长的标题
        card_width = 288  # 增加卡片宽度
        scroll_width = self.scroll_area.width()
        
        # 如果滚动区域宽度为0（未初始化），使用默认值
        if scroll_width <= 1:
            scroll_width = 800  # 默认宽度
        
        # 计算每行可以放置的卡片数量
        columns = max(1, scroll_width // card_width)
        
        # 使用网格布局
        for i, countdown in enumerate(countdowns):
            row = i // columns
            col = i % columns
            
            # 创建倒计时卡片框架
            countdown_frame = QFrame()
            countdown_frame.setFrameStyle(QFrame.Box)
            countdown_frame.setLineWidth(1)
            countdown_frame.setFixedSize(card_width, 100)  # 固定大小
            
            # 检查是否被选中
            is_selected = self.selected_countdown_id == countdown["id"]
            if is_selected:
                countdown_frame.setStyleSheet("QFrame { background-color: lightblue; border: 2px solid blue; }")
            else:
                countdown_frame.setStyleSheet("QFrame { background-color: white; }")
            
            # 设置网格列权重，使列均匀分布
            self.scroll_layout.setColumnStretch(col, 1)
            
            # 绑定点击事件来选择倒计时
            countdown_id = countdown["id"]
            countdown_frame.mousePressEvent = lambda event, cid=countdown_id: self.select_countdown(cid)
            
            # 计算剩余时间 - 精确到秒
            target_time_str = countdown.get("target_time", "23:59:00")
            
            # 尝试解析包含秒数的时间格式
            try:
                # 先尝试包含秒数的格式
                time_format = "%Y-%m-%d %H:%M:%S"
                target_datetime = datetime.strptime(
                    f"{countdown['target_date']} {target_time_str}", 
                    time_format
                )
            except ValueError:
                # 如果不包含秒数，使用默认格式
                try:
                    time_format = "%Y-%m-%d %H:%M"
                    target_datetime = datetime.strptime(
                        f"{countdown['target_date']} {target_time_str}", 
                        time_format
                    )
                except ValueError:
                    # 如果还是失败，使用默认时间
                    target_datetime = datetime.strptime(
                        f"{countdown['target_date']} 23:59:00", 
                        "%Y-%m-%d %H:%M:%S"
                    )
            
            now = datetime.now()
            time_left = target_datetime - now
            
            # 检查倒计时是否结束
            if self.check_countdown_finished(countdown_id, countdown):
                continue
            
            if time_left.total_seconds() <= 0:
                remaining_str = "已过期"
            else:
                days = time_left.days
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                seconds = time_left.seconds % 60
                
                # 根据剩余时间选择合适的显示格式
                if days > 0:
                    remaining_str = f"{days}天 {hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    remaining_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # 创建卡片布局
            card_layout = QVBoxLayout(countdown_frame)
            
            # 第一行：剩余时间（大字体）
            remaining_label = QLabel(remaining_str)
            remaining_label.setFont(QFont("Arial", 14, QFont.Bold))
            if time_left.total_seconds() <= 0:
                remaining_label.setStyleSheet("color: red;")
            else:
                remaining_label.setStyleSheet("color: blue;")
            remaining_label.setAlignment(Qt.AlignCenter)
            remaining_label.mousePressEvent = lambda event, cid=countdown_id: self.select_countdown(cid)
            card_layout.addWidget(remaining_label)
            
            # 第二行：事件名称
            # 如果名称太长，截断并添加省略号
            name = countdown["name"]
            if len(name) > 20:  # 限制名称长度
                name = name[:20] + "..."
                
            name_label = QLabel(name)
            name_label.setFont(QFont("Arial", 10, QFont.Bold))
            name_label.setAlignment(Qt.AlignCenter)
            name_label.mousePressEvent = lambda event, cid=countdown_id: self.select_countdown(cid)
            card_layout.addWidget(name_label)
            
            # 第三行：目标时间
            # 格式化显示目标时间（如果包含秒数，去掉秒数以保持简洁）
            display_time = target_time_str
            if ":" in target_time_str and target_time_str.count(":") == 2:
                # 如果包含秒数，只显示到分钟
                display_time = ":".join(target_time_str.split(":")[:2])
            
            target_time_str_display = f"{countdown['target_date']} {display_time}"
            target_label = QLabel(f"目标: {target_time_str_display}")
            target_label.setFont(QFont("Arial", 9))
            target_label.setAlignment(Qt.AlignCenter)
            target_label.mousePressEvent = lambda event, cid=countdown_id: self.select_countdown(cid)
            card_layout.addWidget(target_label)
            
            # 添加到网格布局
            self.scroll_layout.addWidget(countdown_frame, row, col, Qt.AlignCenter)
            self.countdown_cards[countdown_id] = countdown_frame
    
    def resizeEvent(self, event):
        """当窗口大小改变时，重新计算列数"""
        super().resizeEvent(event)
        # 刷新倒计时列表以重新布局
        self.refresh_countdowns()