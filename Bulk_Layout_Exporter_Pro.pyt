# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Bulk Layout Exporter (Advanced Edition with Zoom Control & KMZ)
# Developed By Eng Omar Adel Heiba
# ---------------------------------------------------------------------------

import arcpy
import os

class Toolbox(object):
    def __init__(self):
        self.label = "Bulk Layout Exporter | المُصدِّر الذكي للخرائط"
        self.alias = "BulkLayoutExporter"
        self.description = "Automated tool to export Maps with dynamic naming, Zoom Control, and KMZ. Developed By Eng Omar Adel Heiba."
        self.tools = [BulkExporter]

class BulkExporter(object):
    def __init__(self):
        self.label = "Bulk Layout Exporter | تصدير الخرائط المجمع"
        self.description = "Exports layouts dynamically based on Map Series or a selected Layer/Field with Zoom Control and KMZ support. Developed By Eng Omar Adel Heiba."
        self.canRunInBackground = True

    def getParameterInfo(self):
        param_aprx = arcpy.Parameter(displayName="ArcGIS Project (.aprx) | مشروع آرك جي آي إس", name="in_aprx", datatype="DEFile", parameterType="Required", direction="Input")
        param_aprx.value = "CURRENT"

        param_layout = arcpy.Parameter(displayName="Layout Name | اسم اللوحة", name="layout_name", datatype="GPString", parameterType="Required", direction="Input")

        param_format = arcpy.Parameter(displayName="Export Format | صيغة التصدير", name="export_format", datatype="GPString", parameterType="Required", direction="Input")
        param_format.filter.list = ["PDF", "JPEG", "PNG"]
        param_format.value = "PDF"

        param_folder = arcpy.Parameter(displayName="Output Folder | مسار مجلد الحفظ", name="out_folder", datatype="DEFolder", parameterType="Required", direction="Input")

        param_dpi = arcpy.Parameter(displayName="Resolution (DPI) | دقة التصدير", name="resolution", datatype="GPLong", parameterType="Required", direction="Input")
        param_dpi.value = 300

        param_layer = arcpy.Parameter(displayName="Index Layer (Optional) | طبقة التقسيم (اختياري)", name="index_layer", datatype="GPFeatureLayer", parameterType="Optional", direction="Input")
        
        param_field = arcpy.Parameter(displayName="Name Field (Optional) | حقل التسمية (اختياري)", name="name_field", datatype="Field", parameterType="Optional", direction="Input")
        param_field.parameterDependencies = [param_layer.name]

        # معامل التحكم في الزوم
        param_zoom = arcpy.Parameter(displayName="Zoom Margin (%) | نسبة الهامش حول العنصر", name="zoom_margin", datatype="GPLong", parameterType="Optional", direction="Input")
        param_zoom.value = 10  # افتراضياً يترك 10% مساحة حول العنصر

        param_kmz = arcpy.Parameter(displayName="Export KMZ for each map | استخراج ملف KMZ لكل خريطة", name="export_kmz", datatype="GPBoolean", parameterType="Optional", direction="Input")
        param_kmz.value = False

        return [param_aprx, param_layout, param_format, param_folder, param_dpi, param_layer, param_field, param_zoom, param_kmz]

    def execute(self, parameters, messages):
        aprx_path = parameters[0].valueAsText
        layout_name = parameters[1].valueAsText
        export_format = parameters[2].valueAsText
        out_folder = parameters[3].valueAsText
        dpi = parameters[4].value
        index_layer = parameters[5].valueAsText
        name_field = parameters[6].valueAsText
        
        zoom_margin = parameters[7].value
        if zoom_margin is None: 
            zoom_margin = 10
            
        export_kmz = parameters[8].value

        arcpy.AddMessage("Initializing Project... | جاري تهيئة المشروع...")
        aprx = arcpy.mp.ArcGISProject(aprx_path)
        
        layout_list = aprx.listLayouts(layout_name)
        if not layout_list:
            arcpy.AddError(f"Layout '{layout_name}' not found! | لم يتم العثور على اللوحة.")
            return
        
        layout = layout_list[0]
        mf = layout.listElements("MAPFRAME_ELEMENT")[0]
        target_map = mf.map

        if layout.mapSeries and layout.mapSeries.enabled:
            ms = layout.mapSeries
            total_pages = ms.pageCount
            arcpy.AddMessage(f"Map Series Enabled: Found {total_pages} pages.")
            
            arcpy.SetProgressor("step", f"Exporting {export_format}...", 0, total_pages, 1)
            for page_num in range(1, total_pages + 1):
                ms.currentPageNumber = page_num
                
                try:
                    page_name = str(ms.pageRow.getValue(ms.pageNameField.name))
                    for char in '<>:"/\\|?*': page_name = page_name.replace(char, '_')
                except:
                    page_name = f"Map_{page_num}"
                
                out_file = os.path.join(out_folder, f"{page_name}.{export_format.lower()}")
                
                if export_format == "PDF": layout.exportToPDF(out_file, resolution=dpi)
                elif export_format == "JPEG": layout.exportToJPEG(out_file, resolution=dpi)
                elif export_format == "PNG": layout.exportToPNG(out_file, resolution=dpi)
                
                if export_kmz:
                    kmz_out = os.path.join(out_folder, f"{page_name}.kmz")
                    arcpy.conversion.MapToKML(target_map, kmz_out, mf.camera.scale)
                    
                arcpy.SetProgressorPosition(page_num)
                arcpy.AddMessage(f"Exported: {page_name}")
                
            arcpy.ResetProgressor()

        elif index_layer and name_field:
            arcpy.AddMessage("Using Manual Iteration with Custom Zoom... | جاري الاستخراج اليدوي مع التحكم في الزوم...")
            
            with arcpy.da.SearchCursor(index_layer, ['SHAPE@', name_field]) as cursor:
                for row in cursor:
                    geom = row[0]
                    page_name = str(row[1])
                    for char in '<>:"/\\|?*': page_name = page_name.replace(char, '_')
                    
                    # ضبط الكاميرا وتطبيق الهامش المخصص للزوم
                    mf.camera.setExtent(geom.extent)
                    mf.camera.scale = mf.camera.scale * (1.0 + (zoom_margin / 100.0))
                    
                    out_file = os.path.join(out_folder, f"{page_name}.{export_format.lower()}")
                    
                    if export_format == "PDF": layout.exportToPDF(out_file, resolution=dpi)
                    elif export_format == "JPEG": layout.exportToJPEG(out_file, resolution=dpi)
                    elif export_format == "PNG": layout.exportToPNG(out_file, resolution=dpi)
                    
                    if export_kmz:
                        kmz_out = os.path.join(out_folder, f"{page_name}.kmz")
                        arcpy.conversion.MapToKML(target_map, kmz_out, mf.camera.scale)
                        
                    arcpy.AddMessage(f"Exported: {page_name} (Zoom Margin: {zoom_margin}%)")
        else:
            arcpy.AddError("Please enable Map Series OR provide an Index Layer & Name Field.")

        arcpy.AddMessage("--------------------------------------------------")
        arcpy.AddMessage("Developed By Eng Omar Adel Heiba")
        arcpy.AddMessage("--------------------------------------------------")
        return