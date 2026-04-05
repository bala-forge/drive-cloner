#!/usr/bin/env python3
"""
Disk Manager - GTK3 Disk Cloner with Multiple Operations
Features: Clone, Create IMG
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import threading
import re
import time
from datetime import datetime
import os
import sys
import getpass
import pwd
import grp


class DiskManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="Drive Cloner")
        self.set_default_size(750, 750)
        self.set_resizable(False)
        
        # Check if running as root
        self.is_root = os.geteuid() == 0
        
        # Create headerbar for title
        header = Gtk.HeaderBar()
        header_title = "Drive Cloner"
        header.set_title(header_title)
        header.set_show_close_button(True)
        
        # Apply root mode styling
        header.get_style_context().add_class("root-mode")
            
        self.set_titlebar(header)

        self.is_running = False
        self.total_bytes = 0
        self.copied_bytes = 0
        self.start_time = 0
        self.current_process = None
        self.current_operation = "clone"  # clone, create_img, flash_img

        self.load_css()
        self.create_ui()
        self.load_drives()
        
        # Exit if not running as root
        if not self.is_root:
            self.show_root_required_dialog()
            sys.exit(1)

    # --------------------------------------------------
    def show_root_required_dialog(self):
        """Show dialog and exit when not running as root"""
        dialog = Gtk.MessageDialog(
            parent=None,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            message_format="🛡️ Root Privileges Required"
        )
        dialog.format_secondary_text(
            f"You are running as user: {getpass.getuser()}\n\n"
            "Drive Manager Pro requires root privileges to access raw disk devices.\n\n"
            "To run this application:\n"
            "1. Run: sudo python3 clone.py\n"
            "2. Or: pkexec python3 clone.py\n\n"
            "Application will now exit."
        )
        
        dialog.run()
        dialog.destroy()

    # --------------------------------------------------
    def load_css(self):
        css = b"""
        window {
            background-color: #f5f7fb;
            font-size: 15px;
        }

        headerbar {
            background: linear-gradient(to right, #1e40af, #3b82f6, #1e40af);
            color: white;
            font-weight: bold;
        }

        headerbar.root-mode {
            background: linear-gradient(to right, #1e40af, #3b82f6, #1e40af);
        }

        .warning-frame {
            background-color: #fef3c7;
            border: 2px solid #f59e0b;
            border-radius: 8px;
        }

        .warning-label {
            color: #92400e;
            font-weight: bold;
        }

        label.root-badge {
            background-color: #dc2626;
            color: #ffffff;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 4px;
        }


        headerbar > label {
            color: white;
            font-weight: bold;
        }

        headerbar button {
            background: none;
            border: none;
            box-shadow: none;
            padding: 8px;
            margin: 4px;
            min-width: 24px;
            min-height: 24px;
            border-radius: 4px;
            color: black;
        }

        headerbar button:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        headerbar button.titlebutton {
            background: none;
            border: none;
            box-shadow: none;
            padding: 8px;
            margin: 4px;
            min-width: 24px;
            min-height: 24px;
            border-radius: 4px;
            color: black;
        }

        headerbar button.titlebutton:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        frame {
            background-color: #ffffff;
            border-radius: 8px;
            border: 1px solid #d0d7e2;
        }

        label {
            font-size: 15px;
            font-weight: bold;
            color: #374151;
        }

        comboboxentry {
            padding: 6px;
            border-radius: 10px;
        }

        entry {
            padding: 6px;
            border-radius: 6px;
        }

        progressbar {
            min-height: 30px;
            font-weight: bold;
            color: black;
            text-shadow: 1px 1px 1px rgba(255,255,255,0.8);
        }

        .progress-label {
            font-size: 16px;
            font-weight: bold;
            color: #1f2937;
        }

        dialog {
            background-color: white;
        }

        messagedialog {
            background-color: white;
        }

        label {
            color: black;
        }

        .dialog-label {
            color: black;
            font-weight: bold;
        }

        .ok-button {
            background-color: #ef4444;
            color: white;
            font-weight: bold;
            font-size: 16px;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
        }

        .ok-button:hover {
            background-color: #dc2626;
        }

        .cancel-button {
            background-color: #6b7280;
            color: white;
            font-weight: bold;
            font-size: 16px;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
        }

        .cancel-button:hover {
            background-color: #4b5563;
        }

        messagedialog button {
            margin: 5px;
            min-width: 80px;
        }

        button {
            font-size: 16px;
        }

        messagedialog {
            font-size: 16px;
        }

        messagedialog label {
            font-size: 16px;
            color: black;
        }

        .footer {
            background-color: #f1f5f9;
            border-top: 2px solid #cbd5e1;
            padding: 10px;
            margin-top: 10px;
        }

        .footer label {
            color: #475569;
            font-size: 13px;
            font-weight: bold;
        }

        progressbar trough {
            background: #e5e7eb;
            border-radius: 6px;
            min-height: 30px;
        }

        progressbar progress {
            background: linear-gradient(to right, #16a34a, #22c55e, #16a34a);
            border-radius: 6px;
            min-height: 30px;
        }

        button {
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
        }

        .refresh-button { background: #2563eb; color: white; }
        .refresh-button:hover { background: #1d4ed8; }

        .clear-button { background: #dc2626; color: white; }
        .clear-button:hover { background: #b91c1c; }

        .start-button { background: #16a34a; color: white; }
        .start-button:hover { background: #15803d; }

        .stop-button { background: #ea580c; color: white; }
        .stop-button:hover { background: #c2410c; }

        .operation-button {
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
        }

        .op-clone { background: #3b82f6; color: white; }
        .op-clone:hover { background: #2563eb; }
        
        .op-create { background: #8b5cf6; color: white; }
        .op-create:hover { background: #7c3aed; }

        .op-selected {
            border: 3px solid #fbbf24;
            box-shadow: 0 0 15px rgba(251, 191, 36, 0.7);
            font-weight: bold;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
        }

        textview {
            background: #0f172a;
            color: #e5e7eb;
            font-family: monospace;
        }
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # --------------------------------------------------
    def padded_box(self, spacing=8):
        box = Gtk.Box(spacing=spacing)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        return box

    # --------------------------------------------------
    def create_ui(self):
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main.set_margin_top(12)
        main.set_margin_bottom(12)
        main.set_margin_start(12)
        main.set_margin_end(12)
        self.add(main)


        title = Gtk.Label()
        title.set_markup("<b><big>Drive Cloner</big></b>")
        main.pack_start(title, False, False, 0)

        # ---------- OPERATION SELECTOR ----------
        op_frame = Gtk.Frame(label="Select Operation")
        op_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        op_box.set_margin_top(12)
        op_box.set_margin_bottom(12)
        op_box.set_margin_start(12)
        op_box.set_margin_end(12)
        op_frame.add(op_box)

        self.clone_btn = Gtk.Button(label="🔄 Clone Drive")
        self.clone_btn.get_style_context().add_class("operation-button")
        self.clone_btn.get_style_context().add_class("op-clone")
        self.clone_btn.get_style_context().add_class("op-selected")
        self.clone_btn.connect("clicked", self.on_operation_change, "clone")
        op_box.pack_start(self.clone_btn, True, True, 0)

        self.create_btn = Gtk.Button(label="💾 Create IMG")
        self.create_btn.get_style_context().add_class("operation-button")
        self.create_btn.get_style_context().add_class("op-create")
        self.create_btn.connect("clicked", self.on_operation_change, "create_img")
        op_box.pack_start(self.create_btn, True, True, 0)

        main.pack_start(op_frame, False, False, 0)

        # ---------- DYNAMIC CONTENT AREA ----------
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main.pack_start(self.content_box, False, False, 0)

        # ---------- BLOCK SIZE ----------
        bs_frame = Gtk.Frame(label="Block Size")
        bs_box = self.padded_box()
        bs_frame.add(bs_box)

        self.block_combo = Gtk.ComboBoxText()
        block_sizes = [
            ("512K", "Low RAM (<2GB) - Most reliable"),
            ("1M", "Low RAM (<2GB) - Reliable"),
            ("2M", "2GB+ RAM - Good balance"),
            ("4M", "4GB+ RAM - Standard choice"),
            ("8M", "4GB+ RAM - Faster"),
            ("16M", "8GB+ RAM - Fast"),
            ("32M", "8GB+ RAM - Very Fast ⚡"),
            ("64M", "16GB+ RAM - Maximum speed")
        ]
        
        for bs, tooltip in block_sizes:
            self.block_combo.append_text(bs)
        
        self.block_combo.set_active(6)
        bs_box.pack_start(self.block_combo, True, True, 0)
        
        self.block_help_label = Gtk.Label()
        self.block_help_label.set_markup(f"<small><i>{block_sizes[6][1]}</i></small>")
        self.block_help_label.set_xalign(0)
        bs_box.pack_start(self.block_help_label, False, False, 0)
        
        self.block_combo.connect("changed", self.on_block_size_changed, block_sizes)

        main.pack_start(bs_frame, False, False, 0)

        # ---------- PROGRESS ----------
        p_frame = Gtk.Frame(label="Progress")
        p_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        p_box.set_margin_top(8)
        p_box.set_margin_bottom(8)
        p_box.set_margin_start(8)
        p_box.set_margin_end(8)
        p_frame.add(p_box)

        self.progress_bar = Gtk.ProgressBar(show_text=True)
        p_box.pack_start(self.progress_bar, True, True, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.copied_label = Gtk.Label()
        self.copied_label.get_style_context().add_class("progress-label")
        self.speed_label = Gtk.Label()
        self.speed_label.get_style_context().add_class("progress-label")
        self.eta_label = Gtk.Label()
        self.eta_label.get_style_context().add_class("progress-label")
        
        info.pack_start(self.copied_label, True, True, 0)
        info.pack_start(self.speed_label, True, True, 0)
        info.pack_end(self.eta_label, False, False, 0)

        p_box.pack_start(info, False, False, 0)
        main.pack_start(p_frame, False, False, 0)

        # ---------- LOG ----------
        log_frame = Gtk.Frame(label="Activity Log")
        log_box = self.padded_box()
        log_frame.add(log_box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_size_request(-1, 150)

        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        scrolled.add(self.log_view)
        log_box.pack_start(scrolled, True, True, 0)

        main.pack_start(log_frame, True, True, 0)

        # ---------- BUTTONS ----------
        btn_box = Gtk.Box(spacing=10)

        self.refresh_btn = Gtk.Button(label="Refresh Drives")
        self.refresh_btn.get_style_context().add_class("refresh-button")
        self.refresh_btn.connect("clicked", self.on_refresh)
        btn_box.pack_start(self.refresh_btn, False, False, 0)

        self.clear_btn = Gtk.Button(label="Clear Logs")
        self.clear_btn.get_style_context().add_class("clear-button")
        self.clear_btn.connect("clicked", self.on_clear)
        btn_box.pack_start(self.clear_btn, False, False, 0)

        self.start_btn = Gtk.Button(label="Start Clone")
        self.start_btn.get_style_context().add_class("start-button")
        self.start_btn.connect("clicked", self.on_start)
        btn_box.pack_end(self.start_btn, False, False, 0)

        main.pack_start(btn_box, False, False, 0)

        # ---------- FOOTER ----------
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        footer.get_style_context().add_class("footer")
        footer.set_margin_top(10)
        footer.set_margin_bottom(10)
        footer.set_margin_start(12)
        footer.set_margin_end(12)
        
        left_footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        right_footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        footer_label = Gtk.Label()
        footer_label.set_text("Developed by P B krishna")
        footer_label.set_xalign(0.5)
        left_footer.pack_start(footer_label, True, True, 0)
        
        # Center the footer
        footer.pack_start(left_footer, True, True, 0)
        
        main.pack_start(footer, False, False, 0)

        # Build initial UI for clone operation
        self.build_clone_ui()
        
        self.log("Application ready")

    # --------------------------------------------------
    def on_operation_change(self, button, operation):
        if self.is_running:
            self.log("Cannot change operation while task is running")
            return
            
        self.current_operation = operation
        
        # Update button selection styling
        self.clone_btn.get_style_context().remove_class("op-selected")
        self.create_btn.get_style_context().remove_class("op-selected")
        button.get_style_context().add_class("op-selected")
        
        # Clear content box
        for child in self.content_box.get_children():
            self.content_box.remove(child)
        
        # Build appropriate UI
        if operation == "clone":
            self.build_clone_ui()
            self.start_btn.set_label("Start Clone")
        elif operation == "create_img":
            self.build_create_img_ui()
            self.start_btn.set_label("Create IMG")
        
        self.content_box.show_all()
        self.log(f"Switched to {operation.replace('_', ' ').title()} operation")

    # --------------------------------------------------
    def build_clone_ui(self):
        drives_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        # SOURCE
        src_frame = Gtk.Frame(label="Source Drive")
        src_box = self.padded_box()
        src_frame.add(src_box)

        self.source_store = Gtk.ListStore(str)
        self.source_combo = Gtk.ComboBox.new_with_model(self.source_store)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", 3)
        self.source_combo.pack_start(renderer, True)
        self.source_combo.add_attribute(renderer, "text", 0)
        src_box.pack_start(self.source_combo, True, True, 0)

        drives_container.pack_start(src_frame, True, True, 0)

        # DEST
        dst_frame = Gtk.Frame(label="Destination Drive")
        dst_box = self.padded_box()
        dst_frame.add(dst_box)

        self.dest_store = Gtk.ListStore(str)
        self.dest_combo = Gtk.ComboBox.new_with_model(self.dest_store)
        renderer2 = Gtk.CellRendererText()
        renderer2.set_property("ellipsize", 3)
        self.dest_combo.pack_start(renderer2, True)
        self.dest_combo.add_attribute(renderer2, "text", 0)
        dst_box.pack_start(self.dest_combo, True, True, 0)

        drives_container.pack_start(dst_frame, True, True, 0)

        self.content_box.pack_start(drives_container, False, False, 0)
        self.load_drives()

    # --------------------------------------------------
    def build_create_img_ui(self):
        drives_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        drives_container.set_homogeneous(True)
        
        # SOURCE DRIVE
        src_frame = Gtk.Frame(label="Source Drive")
        src_box = self.padded_box()
        src_frame.add(src_box)

        self.source_store = Gtk.ListStore(str)
        self.source_combo = Gtk.ComboBox.new_with_model(self.source_store)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", 3)
        self.source_combo.pack_start(renderer, True)
        self.source_combo.add_attribute(renderer, "text", 0)
        src_box.pack_start(self.source_combo, True, True, 0)

        drives_container.pack_start(src_frame, True, True, 0)

        # DESTINATION (IMG FILE)
        dst_frame = Gtk.Frame(label="Destination IMG File")
        dst_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dst_box.set_margin_top(8)
        dst_box.set_margin_bottom(8)
        dst_box.set_margin_start(8)
        dst_box.set_margin_end(8)
        dst_frame.add(dst_box)

        self.img_path_entry = Gtk.Entry()
        self.img_path_entry.set_placeholder_text("/path/to/backup.img")
        dst_box.pack_start(self.img_path_entry, True, True, 0)

        browse_btn = Gtk.Button(label="Browse...")
        browse_btn.connect("clicked", self.on_browse_save)
        dst_box.pack_start(browse_btn, False, False, 0)

        drives_container.pack_start(dst_frame, True, True, 0)

        self.content_box.pack_start(drives_container, False, False, 0)
        self.load_drives()

    # --------------------------------------------------
    def on_browse_save(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Save IMG File",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_current_name("backup.img")
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.img_path_entry.set_text(dialog.get_filename())
        dialog.destroy()

    # --------------------------------------------------
    def on_block_size_changed(self, combo, block_sizes):
        active = combo.get_active()
        if 0 <= active < len(block_sizes):
            tooltip = block_sizes[active][1]
            self.block_help_label.set_markup(f"<small><i>{tooltip}</i></small>")

    # --------------------------------------------------
    def log(self, msg):
        def update_log():
            t = datetime.now().strftime("%H:%M:%S")
            self.log_buffer.insert(self.log_buffer.get_end_iter(), f"[{t}] {msg}\n")
            end_iter = self.log_buffer.get_end_iter()
            mark = self.log_buffer.create_mark("end", end_iter, False)
            self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
            self.log_buffer.delete_mark(mark)
        
        if threading.current_thread() == threading.main_thread():
            update_log()
        else:
            GLib.idle_add(update_log)

    # --------------------------------------------------
    def on_clear(self, _):
        self.log_buffer.set_text("")
        self.log("Logs cleared")

    # --------------------------------------------------
    def load_drives(self):
        """Load available drives into combo boxes"""
        self.log("Scanning drives...")
        if hasattr(self, 'source_store'):
            self.source_store.clear()
        if hasattr(self, 'dest_store'):
            self.dest_store.clear()

        try:
            out = subprocess.check_output(
                ["lsblk", "-d", "-n", "-o", "NAME,SIZE,MODEL"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            drives = []
            for l in out.splitlines():
                p = l.split(maxsplit=2)
                if re.match(r"(sd|nvme|mmcblk)", p[0]):
                    drives.append(f"/dev/{p[0]} • {p[1]} • {p[2] if len(p)>2 else ''}")

            for d in drives:
                if hasattr(self, 'source_store'):
                    self.source_store.append([d])
                if hasattr(self, 'dest_store'):
                    self.dest_store.append([d])

            if drives:
                if hasattr(self, 'source_combo'):
                    self.source_combo.set_active(0)
                if hasattr(self, 'dest_combo') and len(drives) > 1:
                    self.dest_combo.set_active(1)

            self.log(f"Found {len(drives)} drives")
        except Exception as e:
            self.log(f"Error scanning drives: {str(e)}")

    # --------------------------------------------------
    def on_refresh(self, _):
        self.load_drives()

    # --------------------------------------------------
    def on_start(self, _):
        if self.current_operation == "clone":
            self.start_clone()
        elif self.current_operation == "create_img":
            self.start_create_img()

    # --------------------------------------------------
    def start_clone(self):
        s = self.source_combo.get_active_iter()
        d = self.dest_combo.get_active_iter()
        if not s or not d:
            self.log("Select both drives")
            return

        src = self.source_store[s][0].split("•")[0].strip()
        dst = self.dest_store[d][0].split("•")[0].strip()
        if src == dst:
            self.log("Source and destination cannot be same")
            return

        if not self.show_warning_dialog(
            "⚠️ WARNING: Data Loss Warning",
            f"All data on destination drive {dst} will be PERMANENTLY ERASED!\n\n"
            f"This operation cannot be undone.\n"
            f"Source: {src}\n"
            f"Destination: {dst}\n\n"
            f"Click OK to proceed or Cancel to abort."
        ):
            return

        self.disable_controls()
        threading.Thread(
            target=self.run_dd,
            args=(src, dst, self.block_combo.get_active_text(), "clone"),
            daemon=True
        ).start()

    # --------------------------------------------------
    def start_create_img(self):
        s = self.source_combo.get_active_iter()
        if not s:
            self.log("Select source drive")
            return

        img_path = self.img_path_entry.get_text().strip()
        if not img_path:
            self.log("Enter output IMG file path")
            return

        src = self.source_store[s][0].split("•")[0].strip()

        if not self.show_warning_dialog(
            "📀 Create IMG Backup",
            f"This will create a backup image of:\n"
            f"Source: {src}\n"
            f"Output: {img_path}\n\n"
            f"This may take a while depending on drive size.\n\n"
            f"Click OK to proceed or Cancel to abort."
        ):
            return

        self.disable_controls()
        threading.Thread(
            target=self.run_dd,
            args=(src, img_path, self.block_combo.get_active_text(), "create_img"),
            daemon=True
        ).start()

    # --------------------------------------------------
    def show_warning_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            message_format=title
        )
        dialog.set_default_size(500, 300)
        dialog.format_secondary_text(message)
        
        # Apply red styling to OK button
        ok_button = dialog.get_widget_for_response(Gtk.ResponseType.OK)
        if ok_button:
            ok_button.get_style_context().add_class("ok-button")
        
        # Apply grey styling to Cancel button
        cancel_button = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        if cancel_button:
            cancel_button.get_style_context().add_class("cancel-button")
        
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            self.log("Operation cancelled by user")
            return False
        return True

    # --------------------------------------------------
    def check_write_access(self, device_path):
        """Check if we have write access to a device"""
        try:
            if device_path.startswith('/dev/'):
                # For block devices, check if we're root or have write permissions
                if self.is_root:
                    return True
                
                # Check if user is in disk group
                try:
                    disk_group = grp.getgrnam('disk')
                    current_groups = os.getgroups()
                    if disk_group.gr_gid in current_groups:
                        return True
                except:
                    pass
                
                # Check direct permissions
                if os.access(device_path, os.W_OK):
                    return True
                
                return False
            else:
                # For files, check regular permissions
                return os.access(os.path.dirname(device_path), os.W_OK)
        except:
            return False

    # --------------------------------------------------
    def disable_controls(self):
        self.start_btn.set_sensitive(False)
        if hasattr(self, 'source_combo'):
            self.source_combo.set_sensitive(False)
        if hasattr(self, 'dest_combo'):
            self.dest_combo.set_sensitive(False)
        if hasattr(self, 'img_path_entry'):
            self.img_path_entry.set_sensitive(False)
        self.block_combo.set_sensitive(False)
        self.clone_btn.set_sensitive(False)
        self.create_btn.set_sensitive(False)

    # --------------------------------------------------
    def enable_controls(self):
        self.start_btn.set_sensitive(True)
        if hasattr(self, 'source_combo'):
            self.source_combo.set_sensitive(True)
        if hasattr(self, 'dest_combo'):
            self.dest_combo.set_sensitive(True)
        if hasattr(self, 'img_path_entry'):
            self.img_path_entry.set_sensitive(True)
        self.block_combo.set_sensitive(True)
        self.clone_btn.set_sensitive(True)
        self.create_btn.set_sensitive(True)

    # --------------------------------------------------
    def run_dd(self, src, dst, bs, operation):
        self.is_running = True
        self.start_time = time.time()

        # Get total bytes based on operation
        try:
            # For clone and create_img, size is the source drive/file size
            if src.startswith('/dev/'):
                # Use blockdev for block devices
                try:
                    self.total_bytes = int(
                        subprocess.check_output(
                            ["blockdev", "--getsize64", src],
                            stderr=subprocess.DEVNULL,
                            text=True
                        ).strip()
                    )
                except subprocess.CalledProcessError:
                    # Fallback for non-root or if blockdev fails
                    if os.path.exists(src):
                        # Try to get size from lsblk
                        try:
                            result = subprocess.check_output(
                                ["lsblk", "-b", "-n", "-o", "SIZE", src],
                                stderr=subprocess.DEVNULL,
                                text=True
                            ).strip()
                            if result:
                                self.total_bytes = int(result)
                        except:
                            self.total_bytes = 0
                    else:
                        self.total_bytes = 0
            else:
                # For regular files
                if os.path.exists(src):
                    self.total_bytes = os.path.getsize(src)
                else:
                    self.total_bytes = 0
        except Exception as e:
            GLib.idle_add(self.log, f"Warning getting size: {e}")
            self.total_bytes = 0

        cmd = ["dd", f"if={src}", f"of={dst}", f"bs={bs}", "status=progress"]
        
        
        op_names = {
            "clone": "Cloning",
            "create_img": "Creating IMG"
        }
        self.log(f"{op_names[operation]}: {src} → {dst} (bs={bs})")

        try:
            self.current_process = subprocess.Popen(
                cmd, 
                stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )

            # Monitor progress
            while True:
                line = self.current_process.stderr.readline()
                if not line and self.current_process.poll() is not None:
                    break
                    
                if line:
                    line = line.strip()
                    if line:
                        self.log(f"DD: {line}")
                        # Parse progress from dd output
                        m = re.search(r"(\d+)\s+bytes", line)
                        if m:
                            copied = int(m.group(1))
                            self.update_progress(copied)
                        else:
                            # Try alternative format
                            m = re.search(r"(\d+(?:\.\d+)?)([KMGT])?B", line.upper())
                            if m:
                                val = float(m.group(1))
                                unit = m.group(2)
                                if unit == 'K':
                                    copied = val * 1024
                                elif unit == 'M':
                                    copied = val * 1024 * 1024
                                elif unit == 'G':
                                    copied = val * 1024 * 1024 * 1024
                                elif unit == 'T':
                                    copied = val * 1024 * 1024 * 1024 * 1024
                                else:
                                    copied = val
                                self.update_progress(int(copied))

            # Wait for process to complete
            self.current_process.wait()
            
            if self.current_process.returncode == 0:
                GLib.idle_add(self.progress_bar.set_fraction, 1.0)
                GLib.idle_add(self.progress_bar.set_text, "100%")
                GLib.idle_add(self.log, f"{op_names[operation]} completed successfully")
                GLib.idle_add(self.show_completion_dialog, operation)
            else:
                GLib.idle_add(self.log, f"{op_names[operation]} failed with return code {self.current_process.returncode}")

        except Exception as e:
            GLib.idle_add(self.log, f"Error during operation: {e}")
        finally:
            self.is_running = False
            GLib.idle_add(self.enable_controls)

    # --------------------------------------------------
    def update_progress(self, copied):
        """Update progress bar and statistics"""
        if self.total_bytes > 0:
            pct = (copied / self.total_bytes * 100)
        else:
            pct = 0
            
        elapsed = time.time() - self.start_time
        speed = copied / elapsed if elapsed > 0 else 0
        speed_gb = speed / (1024**3)
        
        GLib.idle_add(self.progress_bar.set_fraction, min(pct / 100, 1.0))
        GLib.idle_add(self.progress_bar.set_text, f"{pct:.1f}%")
        GLib.idle_add(self.copied_label.set_text, f"Copied: {copied/(1024**3):.2f} GB")
        GLib.idle_add(self.speed_label.set_text, f"Speed: {speed_gb:.2f} GB/s")
        
        if speed > 0 and self.total_bytes > copied:
            eta = (self.total_bytes - copied) / speed
            if eta < 60:
                eta_str = f"{int(eta)}s"
            elif eta < 3600:
                eta_str = f"{int(eta//60)}m {int(eta%60)}s"
            else:
                eta_str = f"{int(eta//3600)}h {int((eta%3600)//60)}m"
            GLib.idle_add(self.eta_label.set_text, f"ETA: {eta_str}")

    # --------------------------------------------------
    def show_completion_dialog(self, operation):
        titles = {
            "clone": "✅ Cloning Completed Successfully!",
            "create_img": "✅ IMG Creation Completed Successfully!"
        }
        
        messages = {
            "clone": "The disk cloning operation has been completed successfully.\nYour destination drive now contains a copy of the source drive.",
            "create_img": "The IMG file has been created successfully.\nYou can now use this backup image for restoration."
        }
        
        dialog = Gtk.MessageDialog(
            parent=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=titles.get(operation, "✅ Operation Completed!")
        )
        dialog.format_secondary_text(messages.get(operation, "The operation completed successfully."))
        
        # Apply styling to OK button
        ok_button = dialog.get_widget_for_response(Gtk.ResponseType.OK)
        if ok_button:
            ok_button.get_style_context().add_class("ok-button")
        
        dialog.run()
        dialog.destroy()


# --------------------------------------------------
if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        print("🛡️ Root privileges required")
        print("   This application requires root privileges to access disk devices")
        print("   Run with: sudo python3", sys.argv[0])
        print("   Or: pkexec python3", sys.argv[0])
        sys.exit(1)
    
    try:
        app = DiskManager()
        app.connect("destroy", Gtk.main_quit)
        app.show_all()
        Gtk.main()
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)
