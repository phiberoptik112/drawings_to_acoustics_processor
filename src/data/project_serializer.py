"""
Project Serializer - Export/Import projects to/from JSON (.acp) files

This module provides functionality to:
1. Export complete projects to portable JSON files
2. Import projects from JSON files with ID remapping
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from models import get_session, Project
from models.drawing import Drawing
from models.drawing_sets import DrawingSet, DrawingComparison, ChangeItem
from models.space import Space, SpaceNoiseSource, RoomBoundary, SpaceSurfaceMaterial, SurfaceType
from models.hvac import (
    HVACComponent, HVACPath, HVACSegment, SegmentFitting, HVACReceiverResult
)
from models.mechanical import MechanicalUnit, NoiseSource
from models.partition import PartitionType, PartitionScheduleDocument, SpacePartition
from models.material_schedule import MaterialSchedule
from models.rt60_models import RT60CalculationResult, RoomSurfaceInstance
from models.drawing_elements import DrawingElement


# Current file format version
FORMAT_VERSION = "1.0"


class ProjectExporter:
    """Export a project to JSON format"""
    
    def __init__(self):
        self.session = None
    
    def export_to_file(self, project_id: int, output_path: str) -> Tuple[bool, str]:
        """
        Export complete project with all related data to a JSON file.
        
        Args:
            project_id: ID of the project to export
            output_path: Path for the output .acp file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.session = get_session()
            
            # Gather all project data
            export_data = self._gather_project_data(project_id)
            
            if export_data is None:
                return False, f"Project with ID {project_id} not found"
            
            # Write to file with nice formatting
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.session.close()
            return True, f"Project exported successfully to {output_path}"
            
        except Exception as e:
            if self.session:
                self.session.close()
            return False, f"Export failed: {str(e)}"
    
    def _gather_project_data(self, project_id: int) -> Optional[Dict]:
        """Collect all project entities into exportable structure"""
        
        # Get project
        project = self.session.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        
        # Build export structure
        export_data = {
            'format_version': FORMAT_VERSION,
            'export_date': datetime.utcnow().isoformat(),
            'app_version': self._get_app_version(),
            
            # Core project data
            'project': project.to_dict(),
            
            # Drawing sets (must come before drawings for dependency order)
            'drawing_sets': self._export_drawing_sets(project_id),
            
            # Drawings
            'drawings': self._export_drawings(project_id),
            
            # Drawing elements (overlays)
            'drawing_elements': self._export_drawing_elements(project_id),
            
            # Spaces
            'spaces': self._export_spaces(project_id),
            
            # Room boundaries
            'room_boundaries': self._export_room_boundaries(project_id),
            
            # Space surface materials
            'space_surface_materials': self._export_space_surface_materials(project_id),
            
            # HVAC components
            'hvac_components': self._export_hvac_components(project_id),
            
            # HVAC paths
            'hvac_paths': self._export_hvac_paths(project_id),
            
            # HVAC segments
            'hvac_segments': self._export_hvac_segments(project_id),
            
            # Segment fittings
            'segment_fittings': self._export_segment_fittings(project_id),
            
            # Mechanical units
            'mechanical_units': self._export_mechanical_units(project_id),
            
            # Noise sources
            'noise_sources': self._export_noise_sources(project_id),
            
            # Partition types
            'partition_types': self._export_partition_types(project_id),
            
            # Partition schedule documents
            'partition_schedule_documents': self._export_partition_schedule_documents(project_id),
            
            # Space partitions
            'space_partitions': self._export_space_partitions(project_id),
            
            # Material schedules
            'material_schedules': self._export_material_schedules(project_id),
            
            # Drawing comparisons
            'drawing_comparisons': self._export_drawing_comparisons(project_id),
            
            # Change items
            'change_items': self._export_change_items(project_id),
            
            # RT60 calculation results
            'rt60_results': self._export_rt60_results(project_id),
            
            # Room surface instances
            'room_surface_instances': self._export_room_surface_instances(project_id),
            
            # HVAC receiver results
            'receiver_results': self._export_receiver_results(project_id),
            
            # Space noise sources (in-space, no duct path)
            'space_noise_sources': self._export_space_noise_sources(project_id),
        }
        
        return export_data
    
    def _get_app_version(self) -> str:
        """Get the application version"""
        try:
            from utils.version import get_version_info
            return get_version_info().get('version', '1.0.0')
        except ImportError:
            return '1.0.0'
    
    def _export_drawing_sets(self, project_id: int) -> List[Dict]:
        """Export all drawing sets"""
        drawing_sets = self.session.query(DrawingSet).filter(
            DrawingSet.project_id == project_id
        ).all()
        return [ds.to_dict() for ds in drawing_sets]
    
    def _export_drawings(self, project_id: int) -> List[Dict]:
        """Export all drawings"""
        drawings = self.session.query(Drawing).filter(
            Drawing.project_id == project_id
        ).all()
        return [d.to_dict() for d in drawings]
    
    def _export_drawing_elements(self, project_id: int) -> List[Dict]:
        """Export all drawing elements (overlays)"""
        elements = self.session.query(DrawingElement).filter(
            DrawingElement.project_id == project_id
        ).all()
        return [e.to_dict() for e in elements]
    
    def _export_spaces(self, project_id: int) -> List[Dict]:
        """Export all spaces"""
        spaces = self.session.query(Space).filter(
            Space.project_id == project_id
        ).all()
        # Use a simpler dict for export (avoiding computed properties that query DB)
        result = []
        for space in spaces:
            space_dict = {
                'id': space.id,
                'project_id': space.project_id,
                'drawing_id': space.drawing_id,
                'drawing_set_id': space.drawing_set_id,
                'name': space.name,
                'description': space.description,
                'room_type': space.room_type,
                'floor_area': space.floor_area,
                'ceiling_area': space.ceiling_area,
                'ceiling_height': space.ceiling_height,
                'volume': space.volume,
                'wall_area': space.wall_area,
                'total_surface_area': space.total_surface_area,
                'room_id': space.room_id,
                'location_in_project': space.location_in_project,
                'space_type': space.space_type,
                'target_rt60': space.target_rt60,
                'calculated_rt60': space.calculated_rt60,
                # Use new materials system with fallback for serialization
                'ceiling_material': space.get_primary_ceiling_material(),
                'wall_material': space.get_primary_wall_material(),
                'floor_material': space.get_primary_floor_material(),
                # Include all materials from new system
                'ceiling_materials': space.get_all_ceiling_materials(),
                'wall_materials': space.get_all_wall_materials(),
                'floor_materials': space.get_all_floor_materials(),
                'calculated_nc': space.calculated_nc,
                'created_date': space.created_date.isoformat() if space.created_date else None,
                'modified_date': space.modified_date.isoformat() if space.modified_date else None,
            }
            result.append(space_dict)
        return result
    
    def _export_room_boundaries(self, project_id: int) -> List[Dict]:
        """Export all room boundaries"""
        spaces = self.session.query(Space).filter(Space.project_id == project_id).all()
        space_ids = [s.id for s in spaces]
        
        if not space_ids:
            return []
        
        boundaries = self.session.query(RoomBoundary).filter(
            RoomBoundary.space_id.in_(space_ids)
        ).all()
        return [b.to_dict() for b in boundaries]
    
    def _export_space_surface_materials(self, project_id: int) -> List[Dict]:
        """Export all space surface materials"""
        spaces = self.session.query(Space).filter(Space.project_id == project_id).all()
        space_ids = [s.id for s in spaces]
        
        if not space_ids:
            return []
        
        materials = self.session.query(SpaceSurfaceMaterial).filter(
            SpaceSurfaceMaterial.space_id.in_(space_ids)
        ).all()
        return [m.to_dict() for m in materials]
    
    def _export_hvac_components(self, project_id: int) -> List[Dict]:
        """Export all HVAC components"""
        components = self.session.query(HVACComponent).filter(
            HVACComponent.project_id == project_id
        ).all()
        return [c.to_dict() for c in components]
    
    def _export_hvac_paths(self, project_id: int) -> List[Dict]:
        """Export all HVAC paths"""
        paths = self.session.query(HVACPath).filter(
            HVACPath.project_id == project_id
        ).all()
        return [p.to_dict() for p in paths]
    
    def _export_hvac_segments(self, project_id: int) -> List[Dict]:
        """Export all HVAC segments"""
        paths = self.session.query(HVACPath).filter(HVACPath.project_id == project_id).all()
        path_ids = [p.id for p in paths]
        
        if not path_ids:
            return []
        
        segments = self.session.query(HVACSegment).filter(
            HVACSegment.hvac_path_id.in_(path_ids)
        ).all()
        return [s.to_dict() for s in segments]
    
    def _export_segment_fittings(self, project_id: int) -> List[Dict]:
        """Export all segment fittings"""
        paths = self.session.query(HVACPath).filter(HVACPath.project_id == project_id).all()
        path_ids = [p.id for p in paths]
        
        if not path_ids:
            return []
        
        segments = self.session.query(HVACSegment).filter(
            HVACSegment.hvac_path_id.in_(path_ids)
        ).all()
        segment_ids = [s.id for s in segments]
        
        if not segment_ids:
            return []
        
        fittings = self.session.query(SegmentFitting).filter(
            SegmentFitting.segment_id.in_(segment_ids)
        ).all()
        return [f.to_dict() for f in fittings]
    
    def _export_mechanical_units(self, project_id: int) -> List[Dict]:
        """Export all mechanical units"""
        units = self.session.query(MechanicalUnit).filter(
            MechanicalUnit.project_id == project_id
        ).all()
        return [u.to_dict() for u in units]
    
    def _export_noise_sources(self, project_id: int) -> List[Dict]:
        """Export all noise sources"""
        sources = self.session.query(NoiseSource).filter(
            NoiseSource.project_id == project_id
        ).all()
        return [s.to_dict() for s in sources]
    
    def _export_partition_types(self, project_id: int) -> List[Dict]:
        """Export all partition types"""
        partition_types = self.session.query(PartitionType).filter(
            PartitionType.project_id == project_id
        ).all()
        return [pt.to_dict() for pt in partition_types]
    
    def _export_partition_schedule_documents(self, project_id: int) -> List[Dict]:
        """Export all partition schedule documents"""
        docs = self.session.query(PartitionScheduleDocument).filter(
            PartitionScheduleDocument.project_id == project_id
        ).all()
        return [d.to_dict() for d in docs]
    
    def _export_space_partitions(self, project_id: int) -> List[Dict]:
        """Export all space partitions"""
        spaces = self.session.query(Space).filter(Space.project_id == project_id).all()
        space_ids = [s.id for s in spaces]
        
        if not space_ids:
            return []
        
        partitions = self.session.query(SpacePartition).filter(
            SpacePartition.space_id.in_(space_ids)
        ).all()
        return [p.to_dict() for p in partitions]
    
    def _export_material_schedules(self, project_id: int) -> List[Dict]:
        """Export all material schedules"""
        drawing_sets = self.session.query(DrawingSet).filter(
            DrawingSet.project_id == project_id
        ).all()
        ds_ids = [ds.id for ds in drawing_sets]
        
        if not ds_ids:
            return []
        
        schedules = self.session.query(MaterialSchedule).filter(
            MaterialSchedule.drawing_set_id.in_(ds_ids)
        ).all()
        return [s.to_dict() for s in schedules]
    
    def _export_drawing_comparisons(self, project_id: int) -> List[Dict]:
        """Export all drawing comparisons"""
        comparisons = self.session.query(DrawingComparison).filter(
            DrawingComparison.project_id == project_id
        ).all()
        return [c.to_dict() for c in comparisons]
    
    def _export_change_items(self, project_id: int) -> List[Dict]:
        """Export all change items"""
        comparisons = self.session.query(DrawingComparison).filter(
            DrawingComparison.project_id == project_id
        ).all()
        comparison_ids = [c.id for c in comparisons]
        
        if not comparison_ids:
            return []
        
        items = self.session.query(ChangeItem).filter(
            ChangeItem.comparison_id.in_(comparison_ids)
        ).all()
        return [i.to_dict() for i in items]
    
    def _export_rt60_results(self, project_id: int) -> List[Dict]:
        """Export all RT60 calculation results"""
        spaces = self.session.query(Space).filter(Space.project_id == project_id).all()
        space_ids = [s.id for s in spaces]
        
        if not space_ids:
            return []
        
        results = self.session.query(RT60CalculationResult).filter(
            RT60CalculationResult.space_id.in_(space_ids)
        ).all()
        return [r.to_dict() for r in results]
    
    def _export_room_surface_instances(self, project_id: int) -> List[Dict]:
        """Export all room surface instances"""
        spaces = self.session.query(Space).filter(Space.project_id == project_id).all()
        space_ids = [s.id for s in spaces]
        
        if not space_ids:
            return []
        
        instances = self.session.query(RoomSurfaceInstance).filter(
            RoomSurfaceInstance.space_id.in_(space_ids)
        ).all()
        return [i.to_dict() for i in instances]
    
    def _export_receiver_results(self, project_id: int) -> List[Dict]:
        """Export all HVAC receiver results"""
        spaces = self.session.query(Space).filter(Space.project_id == project_id).all()
        space_ids = [s.id for s in spaces]
        
        if not space_ids:
            return []
        
        results = self.session.query(HVACReceiverResult).filter(
            HVACReceiverResult.space_id.in_(space_ids)
        ).all()
        return [r.to_dict() for r in results]
    
    def _export_space_noise_sources(self, project_id: int) -> List[Dict]:
        """Export all space noise sources"""
        spaces = self.session.query(Space).filter(Space.project_id == project_id).all()
        space_ids = [s.id for s in spaces]
        if not space_ids:
            return []
        sources = self.session.query(SpaceNoiseSource).filter(
            SpaceNoiseSource.space_id.in_(space_ids)
        ).all()
        return [s.to_dict() for s in sources]


class ProjectImporter:
    """Import a project from JSON format"""
    
    def __init__(self):
        self.session = None
        self.id_mappings = {}  # {entity_type: {old_id: new_id}}
    
    def import_from_file(self, input_path: str, new_project_name: str = None) -> Tuple[bool, str, Optional[int]]:
        """
        Import project from a JSON file.
        
        Args:
            input_path: Path to the .acp file
            new_project_name: Optional name for the imported project (uses original if None)
            
        Returns:
            Tuple of (success: bool, message: str, new_project_id: Optional[int])
        """
        try:
            # Read and parse file
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate format
            valid, error = self._validate_format(data)
            if not valid:
                return False, f"Invalid file format: {error}", None
            
            self.session = get_session()
            self.id_mappings = {}
            
            # Create all entities with ID remapping
            new_project_id = self._create_with_id_remapping(data, new_project_name)
            
            self.session.commit()
            self.session.close()
            
            return True, f"Project imported successfully (ID: {new_project_id})", new_project_id
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}", None
        except Exception as e:
            if self.session:
                self.session.rollback()
                self.session.close()
            return False, f"Import failed: {str(e)}", None
    
    def _validate_format(self, data: Dict) -> Tuple[bool, str]:
        """Validate JSON structure and version compatibility"""
        
        # Check required top-level keys
        required_keys = ['format_version', 'project']
        for key in required_keys:
            if key not in data:
                return False, f"Missing required key: {key}"
        
        # Check version compatibility
        file_version = data.get('format_version', '0.0')
        major_version = int(file_version.split('.')[0])
        if major_version > int(FORMAT_VERSION.split('.')[0]):
            return False, f"File version {file_version} is newer than supported version {FORMAT_VERSION}"
        
        # Check project data
        project_data = data.get('project', {})
        if not project_data.get('name'):
            return False, "Project name is required"
        
        return True, ""
    
    def _create_with_id_remapping(self, data: Dict, new_project_name: str = None) -> int:
        """Create all entities with new IDs, maintaining relationships"""
        
        # Import in dependency order
        
        # 1. Create Project
        new_project_id = self._import_project(data['project'], new_project_name)
        self.id_mappings['project'] = {data['project']['id']: new_project_id}
        
        # 2. Create Drawing Sets (no dependencies except project)
        if data.get('drawing_sets'):
            self._import_drawing_sets(data['drawing_sets'], new_project_id)
        
        # 3. Create Drawings (depends on project, drawing_set)
        if data.get('drawings'):
            self._import_drawings(data['drawings'], new_project_id)
        
        # 4. Create Partition Types (depends on project only)
        if data.get('partition_types'):
            self._import_partition_types(data['partition_types'], new_project_id)
        
        # 5. Create Partition Schedule Documents (depends on project only)
        if data.get('partition_schedule_documents'):
            self._import_partition_schedule_documents(data['partition_schedule_documents'], new_project_id)
        
        # 6. Create Mechanical Units (depends on project only)
        if data.get('mechanical_units'):
            self._import_mechanical_units(data['mechanical_units'], new_project_id)
        
        # 7. Create Noise Sources (depends on project only)
        if data.get('noise_sources'):
            self._import_noise_sources(data['noise_sources'], new_project_id)
        
        # 8. Create HVAC Components (depends on project, drawing)
        if data.get('hvac_components'):
            self._import_hvac_components(data['hvac_components'], new_project_id)
        
        # 9. Create Spaces (depends on project, drawing, drawing_set)
        if data.get('spaces'):
            self._import_spaces(data['spaces'], new_project_id)
        
        # 10. Create Room Boundaries (depends on space, drawing)
        if data.get('room_boundaries'):
            self._import_room_boundaries(data['room_boundaries'])
        
        # 11. Create Space Surface Materials (depends on space)
        if data.get('space_surface_materials'):
            self._import_space_surface_materials(data['space_surface_materials'])
        
        # 12. Create Space Partitions (depends on space, partition_type, adjacent_space)
        if data.get('space_partitions'):
            self._import_space_partitions(data['space_partitions'])
        
        # 13. Create HVAC Paths (depends on project, space, hvac_component, drawing_set)
        if data.get('hvac_paths'):
            self._import_hvac_paths(data['hvac_paths'], new_project_id)
        
        # 14. Create HVAC Segments (depends on hvac_path, hvac_component)
        if data.get('hvac_segments'):
            self._import_hvac_segments(data['hvac_segments'])
        
        # 15. Create Segment Fittings (depends on segment)
        if data.get('segment_fittings'):
            self._import_segment_fittings(data['segment_fittings'])
        
        # 16. Create Material Schedules (depends on drawing_set)
        if data.get('material_schedules'):
            self._import_material_schedules(data['material_schedules'])
        
        # 17. Create Drawing Comparisons (depends on project, drawing_set)
        if data.get('drawing_comparisons'):
            self._import_drawing_comparisons(data['drawing_comparisons'], new_project_id)
        
        # 18. Create Change Items (depends on comparison, drawing)
        if data.get('change_items'):
            self._import_change_items(data['change_items'])
        
        # 19. Create Drawing Elements (depends on project, drawing)
        if data.get('drawing_elements'):
            self._import_drawing_elements(data['drawing_elements'], new_project_id)
        
        # 20. Create RT60 Results (depends on space)
        if data.get('rt60_results'):
            self._import_rt60_results(data['rt60_results'])
        
        # 21. Create Room Surface Instances (depends on space)
        if data.get('room_surface_instances'):
            self._import_room_surface_instances(data['room_surface_instances'])
        
        # 22. Create Receiver Results (depends on space)
        if data.get('receiver_results'):
            self._import_receiver_results(data['receiver_results'])
        
        if data.get('space_noise_sources'):
            self._import_space_noise_sources(data['space_noise_sources'])
        
        return new_project_id
    
    def _get_new_id(self, entity_type: str, old_id: Optional[int]) -> Optional[int]:
        """Get the new ID for a remapped entity"""
        if old_id is None:
            return None
        mapping = self.id_mappings.get(entity_type, {})
        return mapping.get(old_id)
    
    def _import_project(self, project_data: Dict, new_name: str = None) -> int:
        """Import project and return new ID"""
        project = Project(
            name=new_name or project_data['name'],
            description=project_data.get('description'),
            location=project_data.get('location'),
            default_scale=project_data.get('default_scale', '1:100'),
            default_units=project_data.get('default_units', 'feet'),
        )
        self.session.add(project)
        self.session.flush()  # Get the new ID
        return project.id
    
    def _import_drawing_sets(self, drawing_sets: List[Dict], project_id: int):
        """Import drawing sets"""
        self.id_mappings['drawing_set'] = {}
        
        for ds_data in drawing_sets:
            ds = DrawingSet(
                project_id=project_id,
                name=ds_data['name'],
                phase_type=ds_data.get('phase_type', 'Legacy'),
                description=ds_data.get('description'),
                is_active=ds_data.get('is_active', False),
            )
            self.session.add(ds)
            self.session.flush()
            self.id_mappings['drawing_set'][ds_data['id']] = ds.id
    
    def _import_drawings(self, drawings: List[Dict], project_id: int):
        """Import drawings"""
        self.id_mappings['drawing'] = {}
        
        for d_data in drawings:
            drawing = Drawing(
                project_id=project_id,
                name=d_data['name'],
                description=d_data.get('description'),
                file_path=d_data.get('file_path', ''),
                scale_ratio=d_data.get('scale_ratio'),
                scale_string=d_data.get('scale_string'),
                page_number=d_data.get('page_number', 1),
                width_pixels=d_data.get('width_pixels'),
                height_pixels=d_data.get('height_pixels'),
                drawing_set_id=self._get_new_id('drawing_set', d_data.get('drawing_set_id')),
            )
            self.session.add(drawing)
            self.session.flush()
            self.id_mappings['drawing'][d_data['id']] = drawing.id
    
    def _import_partition_types(self, partition_types: List[Dict], project_id: int):
        """Import partition types"""
        self.id_mappings['partition_type'] = {}
        
        for pt_data in partition_types:
            pt = PartitionType(
                project_id=project_id,
                assembly_id=pt_data['assembly_id'],
                description=pt_data.get('description'),
                stc_rating=pt_data.get('stc_rating'),
                source_document=pt_data.get('source_document'),
                notes=pt_data.get('notes'),
            )
            self.session.add(pt)
            self.session.flush()
            self.id_mappings['partition_type'][pt_data['id']] = pt.id
    
    def _import_partition_schedule_documents(self, docs: List[Dict], project_id: int):
        """Import partition schedule documents"""
        self.id_mappings['partition_schedule_document'] = {}
        
        for doc_data in docs:
            doc = PartitionScheduleDocument(
                project_id=project_id,
                name=doc_data['name'],
                description=doc_data.get('description'),
                file_path=doc_data.get('file_path'),
                managed_file_path=doc_data.get('managed_file_path'),
                page_number=doc_data.get('page_number', 1),
            )
            self.session.add(doc)
            self.session.flush()
            self.id_mappings['partition_schedule_document'][doc_data['id']] = doc.id
    
    def _import_mechanical_units(self, units: List[Dict], project_id: int):
        """Import mechanical units"""
        self.id_mappings['mechanical_unit'] = {}
        
        for u_data in units:
            unit = MechanicalUnit(
                project_id=project_id,
                name=u_data['name'],
                unit_type=u_data.get('unit_type'),
                manufacturer=u_data.get('manufacturer'),
                model_number=u_data.get('model_number'),
                airflow_cfm=u_data.get('airflow_cfm'),
                external_static_inwg=u_data.get('external_static_inwg'),
                power_kw=u_data.get('power_kw'),
                notes=u_data.get('notes'),
                inlet_levels_json=u_data.get('inlet_levels_json'),
                radiated_levels_json=u_data.get('radiated_levels_json'),
                outlet_levels_json=u_data.get('outlet_levels_json'),
                extra_json=u_data.get('extra_json'),
            )
            self.session.add(unit)
            self.session.flush()
            self.id_mappings['mechanical_unit'][u_data['id']] = unit.id
    
    def _import_noise_sources(self, sources: List[Dict], project_id: int):
        """Import noise sources"""
        self.id_mappings['noise_source'] = {}
        
        for s_data in sources:
            source = NoiseSource(
                project_id=project_id,
                name=s_data['name'],
                source_type=s_data.get('source_type'),
                base_noise_dba=s_data.get('base_noise_dba'),
                notes=s_data.get('notes'),
            )
            self.session.add(source)
            self.session.flush()
            self.id_mappings['noise_source'][s_data['id']] = source.id
    
    def _import_hvac_components(self, components: List[Dict], project_id: int):
        """Import HVAC components"""
        self.id_mappings['hvac_component'] = {}
        
        for c_data in components:
            component = HVACComponent(
                project_id=project_id,
                drawing_id=self._get_new_id('drawing', c_data.get('drawing_id')),
                page_number=c_data.get('page_number', 1),  # Store page for multi-page PDFs
                name=c_data['name'],
                component_type=c_data['component_type'],
                custom_type_label=c_data.get('custom_type_label'),
                x_position=c_data['x_position'],
                y_position=c_data['y_position'],
                noise_level=c_data.get('noise_level'),
                cfm=c_data.get('cfm'),
                branch_takeoff_choice=c_data.get('branch_takeoff_choice'),
                has_turning_vanes=c_data.get('has_turning_vanes', False),
                vane_chord_length=c_data.get('vane_chord_length'),
                num_vanes=c_data.get('num_vanes'),
                lining_thickness=c_data.get('lining_thickness'),
                pressure_drop=c_data.get('pressure_drop'),
                is_silencer=c_data.get('is_silencer', False),
                silencer_type=c_data.get('silencer_type'),
                target_noise_reduction=c_data.get('target_noise_reduction'),
                frequency_requirements=c_data.get('frequency_requirements'),
                space_constraints=c_data.get('space_constraints'),
            )
            self.session.add(component)
            self.session.flush()
            self.id_mappings['hvac_component'][c_data['id']] = component.id
    
    def _import_spaces(self, spaces: List[Dict], project_id: int):
        """Import spaces"""
        self.id_mappings['space'] = {}
        
        for s_data in spaces:
            space = Space(
                project_id=project_id,
                drawing_id=self._get_new_id('drawing', s_data.get('drawing_id')),
                drawing_set_id=self._get_new_id('drawing_set', s_data.get('drawing_set_id')),
                name=s_data['name'],
                description=s_data.get('description'),
                room_type=s_data.get('room_type'),
                floor_area=s_data.get('floor_area'),
                ceiling_area=s_data.get('ceiling_area'),
                ceiling_height=s_data.get('ceiling_height'),
                volume=s_data.get('volume'),
                wall_area=s_data.get('wall_area'),
                total_surface_area=s_data.get('total_surface_area'),
                room_id=s_data.get('room_id'),
                location_in_project=s_data.get('location_in_project'),
                space_type=s_data.get('space_type'),
                target_rt60=s_data.get('target_rt60', 0.8),
                calculated_rt60=s_data.get('calculated_rt60'),
                ceiling_material=s_data.get('ceiling_material'),
                wall_material=s_data.get('wall_material'),
                floor_material=s_data.get('floor_material'),
                calculated_nc=s_data.get('calculated_nc'),
            )
            self.session.add(space)
            self.session.flush()
            self.id_mappings['space'][s_data['id']] = space.id
    
    def _import_room_boundaries(self, boundaries: List[Dict]):
        """Import room boundaries"""
        self.id_mappings['room_boundary'] = {}
        
        for b_data in boundaries:
            boundary = RoomBoundary(
                space_id=self._get_new_id('space', b_data['space_id']),
                drawing_id=self._get_new_id('drawing', b_data['drawing_id']),
                page_number=b_data.get('page_number', 1),
                x_position=b_data['x_position'],
                y_position=b_data['y_position'],
                width=b_data['width'],
                height=b_data['height'],
                calculated_area=b_data.get('calculated_area'),
                polygon_points=b_data.get('polygon_points'),
            )
            self.session.add(boundary)
            self.session.flush()
            self.id_mappings['room_boundary'][b_data['id']] = boundary.id
    
    def _import_space_surface_materials(self, materials: List[Dict]):
        """Import space surface materials"""
        for m_data in materials:
            # Convert surface_type string back to enum
            surface_type_str = m_data.get('surface_type')
            surface_type = SurfaceType(surface_type_str) if surface_type_str else None
            
            material = SpaceSurfaceMaterial(
                space_id=self._get_new_id('space', m_data['space_id']),
                surface_type=surface_type,
                material_key=m_data['material_key'],
                order_index=m_data.get('order_index', 0),
            )
            self.session.add(material)
    
    def _import_space_partitions(self, partitions: List[Dict]):
        """Import space partitions"""
        self.id_mappings['space_partition'] = {}
        
        for p_data in partitions:
            partition = SpacePartition(
                space_id=self._get_new_id('space', p_data['space_id']),
                partition_type_id=self._get_new_id('partition_type', p_data.get('partition_type_id')),
                assembly_location=p_data.get('assembly_location'),
                adjacent_space_type=p_data.get('adjacent_space_type'),
                adjacent_space_id=self._get_new_id('space', p_data.get('adjacent_space_id')),
                minimum_stc_required=p_data.get('minimum_stc_required'),
                stc_rating_override=p_data.get('stc_rating_override'),
                notes=p_data.get('notes'),
            )
            self.session.add(partition)
            self.session.flush()
            self.id_mappings['space_partition'][p_data['id']] = partition.id
    
    def _import_hvac_paths(self, paths: List[Dict], project_id: int):
        """Import HVAC paths"""
        self.id_mappings['hvac_path'] = {}
        
        for p_data in paths:
            path = HVACPath(
                project_id=project_id,
                target_space_id=self._get_new_id('space', p_data.get('target_space_id')),
                primary_source_id=self._get_new_id('hvac_component', p_data.get('primary_source_id')),
                drawing_set_id=self._get_new_id('drawing_set', p_data.get('drawing_set_id')),
                name=p_data['name'],
                description=p_data.get('description'),
                path_type=p_data.get('path_type', 'supply'),
                calculated_noise=p_data.get('calculated_noise'),
                calculated_nc=p_data.get('calculated_nc'),
                receiver_distance_ft=p_data.get('receiver_distance_ft'),
                receiver_method=p_data.get('receiver_method'),
            )
            self.session.add(path)
            self.session.flush()
            self.id_mappings['hvac_path'][p_data['id']] = path.id
    
    def _import_hvac_segments(self, segments: List[Dict]):
        """Import HVAC segments"""
        self.id_mappings['hvac_segment'] = {}
        
        for s_data in segments:
            segment = HVACSegment(
                hvac_path_id=self._get_new_id('hvac_path', s_data['hvac_path_id']),
                from_component_id=self._get_new_id('hvac_component', s_data['from_component_id']),
                to_component_id=self._get_new_id('hvac_component', s_data['to_component_id']),
                length=s_data['length'],
                segment_order=s_data['segment_order'],
                duct_width=s_data.get('duct_width'),
                duct_height=s_data.get('duct_height'),
                diameter=s_data.get('diameter'),
                duct_shape=s_data.get('duct_shape', 'rectangular'),
                duct_type=s_data.get('duct_type', 'sheet_metal'),
                insulation=s_data.get('insulation'),
                lining_thickness=s_data.get('lining_thickness'),
                flow_rate=s_data.get('flow_rate'),
                flow_velocity=s_data.get('flow_velocity'),
                distance_loss=s_data.get('distance_loss'),
                duct_loss=s_data.get('duct_loss'),
                fitting_additions=s_data.get('fitting_additions'),
            )
            self.session.add(segment)
            self.session.flush()
            self.id_mappings['hvac_segment'][s_data['id']] = segment.id
    
    def _import_segment_fittings(self, fittings: List[Dict]):
        """Import segment fittings"""
        for f_data in fittings:
            fitting = SegmentFitting(
                segment_id=self._get_new_id('hvac_segment', f_data['segment_id']),
                fitting_type=f_data['fitting_type'],
                quantity=f_data.get('quantity', 1),
                position_on_segment=f_data.get('position_on_segment'),
                noise_adjustment=f_data.get('noise_adjustment'),
            )
            self.session.add(fitting)
    
    def _import_material_schedules(self, schedules: List[Dict]):
        """Import material schedules"""
        self.id_mappings['material_schedule'] = {}
        
        for s_data in schedules:
            schedule = MaterialSchedule(
                drawing_set_id=self._get_new_id('drawing_set', s_data['drawing_set_id']),
                name=s_data['name'],
                description=s_data.get('description'),
                file_path=s_data.get('file_path'),
                managed_file_path=s_data.get('managed_file_path'),
                schedule_type=s_data.get('schedule_type', 'finishes'),
            )
            self.session.add(schedule)
            self.session.flush()
            self.id_mappings['material_schedule'][s_data['id']] = schedule.id
    
    def _import_drawing_comparisons(self, comparisons: List[Dict], project_id: int):
        """Import drawing comparisons"""
        self.id_mappings['drawing_comparison'] = {}
        
        for c_data in comparisons:
            comparison = DrawingComparison(
                project_id=project_id,
                base_set_id=self._get_new_id('drawing_set', c_data['base_set_id']),
                compare_set_id=self._get_new_id('drawing_set', c_data['compare_set_id']),
                comparison_results=c_data.get('comparison_results'),
                notes=c_data.get('notes'),
                total_changes=c_data.get('total_changes', 0),
                critical_changes=c_data.get('critical_changes', 0),
                acoustic_impact_score=c_data.get('acoustic_impact_score'),
            )
            self.session.add(comparison)
            self.session.flush()
            self.id_mappings['drawing_comparison'][c_data['id']] = comparison.id
    
    def _import_change_items(self, items: List[Dict]):
        """Import change items"""
        for i_data in items:
            item = ChangeItem(
                comparison_id=self._get_new_id('drawing_comparison', i_data['comparison_id']),
                element_type=i_data['element_type'],
                change_type=i_data['change_type'],
                base_element_id=i_data.get('base_element_id'),
                compare_element_id=i_data.get('compare_element_id'),
                change_details=i_data.get('change_details'),
                acoustic_impact=i_data.get('acoustic_impact'),
                severity=i_data.get('severity', 'medium'),
                drawing_id=self._get_new_id('drawing', i_data.get('drawing_id')),
                x_position=i_data.get('x_position'),
                y_position=i_data.get('y_position'),
                area_change=i_data.get('area_change'),
                position_delta=i_data.get('position_delta'),
            )
            self.session.add(item)
    
    def _import_drawing_elements(self, elements: List[Dict], project_id: int):
        """Import drawing elements"""
        for e_data in elements:
            element = DrawingElement(
                project_id=project_id,
                drawing_id=self._get_new_id('drawing', e_data.get('drawing_id')),
                page_number=e_data.get('page_number', 1),
                element_type=e_data.get('element_type'),
                element_data=e_data.get('element_data'),
                space_id=self._get_new_id('space', e_data.get('space_id')),
                hvac_path_id=self._get_new_id('hvac_path', e_data.get('hvac_path_id')),
                hvac_segment_id=self._get_new_id('hvac_segment', e_data.get('hvac_segment_id')),
                hvac_component_id=self._get_new_id('hvac_component', e_data.get('hvac_component_id')),
            )
            self.session.add(element)
    
    def _import_rt60_results(self, results: List[Dict]):
        """Import RT60 calculation results"""
        for r_data in results:
            # Handle nested dict format for frequency data
            rt60_by_freq = r_data.get('rt60_by_frequency', {})
            sabines_by_freq = r_data.get('sabines_by_frequency', {})
            compliance_by_freq = r_data.get('compliance_by_frequency', {})
            
            result = RT60CalculationResult(
                space_id=self._get_new_id('space', r_data['space_id']),
                target_rt60=r_data.get('target_rt60', 0.8),
                target_tolerance=r_data.get('target_tolerance', 0.1),
                room_type=r_data.get('room_type'),
                leed_compliance_required=r_data.get('leed_compliance_required', False),
                calculation_method=r_data.get('calculation_method', 'sabine'),
                room_volume=r_data.get('room_volume'),
                total_sabines_125=sabines_by_freq.get(125) or sabines_by_freq.get('125', 0.0),
                total_sabines_250=sabines_by_freq.get(250) or sabines_by_freq.get('250', 0.0),
                total_sabines_500=sabines_by_freq.get(500) or sabines_by_freq.get('500', 0.0),
                total_sabines_1000=sabines_by_freq.get(1000) or sabines_by_freq.get('1000', 0.0),
                total_sabines_2000=sabines_by_freq.get(2000) or sabines_by_freq.get('2000', 0.0),
                total_sabines_4000=sabines_by_freq.get(4000) or sabines_by_freq.get('4000', 0.0),
                rt60_125=rt60_by_freq.get(125) or rt60_by_freq.get('125', 0.0),
                rt60_250=rt60_by_freq.get(250) or rt60_by_freq.get('250', 0.0),
                rt60_500=rt60_by_freq.get(500) or rt60_by_freq.get('500', 0.0),
                rt60_1000=rt60_by_freq.get(1000) or rt60_by_freq.get('1000', 0.0),
                rt60_2000=rt60_by_freq.get(2000) or rt60_by_freq.get('2000', 0.0),
                rt60_4000=rt60_by_freq.get(4000) or rt60_by_freq.get('4000', 0.0),
                meets_target_125=compliance_by_freq.get(125) or compliance_by_freq.get('125', False),
                meets_target_250=compliance_by_freq.get(250) or compliance_by_freq.get('250', False),
                meets_target_500=compliance_by_freq.get(500) or compliance_by_freq.get('500', False),
                meets_target_1000=compliance_by_freq.get(1000) or compliance_by_freq.get('1000', False),
                meets_target_2000=compliance_by_freq.get(2000) or compliance_by_freq.get('2000', False),
                meets_target_4000=compliance_by_freq.get(4000) or compliance_by_freq.get('4000', False),
                overall_compliance=r_data.get('overall_compliance', False),
                compliance_notes=r_data.get('compliance_notes'),
                average_rt60=r_data.get('average_rt60', 0.0),
                total_surface_area=r_data.get('total_surface_area', 0.0),
                average_absorption_coeff=r_data.get('average_absorption_coeff', 0.0),
            )
            self.session.add(result)
    
    def _import_room_surface_instances(self, instances: List[Dict]):
        """Import room surface instances"""
        for i_data in instances:
            instance = RoomSurfaceInstance(
                space_id=self._get_new_id('space', i_data['space_id']),
                surface_type_id=i_data.get('surface_type_id'),  # Keep original - static reference
                material_id=i_data.get('material_id'),  # Keep original - static reference
                instance_name=i_data['instance_name'],
                instance_number=i_data.get('instance_number', 1),
                calculated_area=i_data.get('calculated_area', 0.0),
                manual_area=i_data.get('manual_area', 0.0),
                use_manual_area=i_data.get('use_manual_area', False),
                area_calculation_notes=i_data.get('area_calculation_notes'),
            )
            self.session.add(instance)
    
    def _import_receiver_results(self, results: List[Dict]):
        """Import HVAC receiver results"""
        for r_data in results:
            result = HVACReceiverResult(
                space_id=self._get_new_id('space', r_data['space_id']),
                target_nc=r_data.get('target_nc'),
                nc_rating=r_data.get('nc_rating'),
                total_dba=r_data.get('total_dba'),
                meets_target=r_data.get('meets_target', False),
                lp_63=r_data.get('lp_63', 0.0),
                lp_125=r_data.get('lp_125', 0.0),
                lp_250=r_data.get('lp_250', 0.0),
                lp_500=r_data.get('lp_500', 0.0),
                lp_1000=r_data.get('lp_1000', 0.0),
                lp_2000=r_data.get('lp_2000', 0.0),
                lp_4000=r_data.get('lp_4000', 0.0),
                room_volume=r_data.get('room_volume'),
                distributed_ceiling_height=r_data.get('distributed_ceiling_height'),
                distributed_floor_area_per_diffuser=r_data.get('distributed_floor_area_per_diffuser'),
                path_parameters_json=r_data.get('path_parameters_json'),
            )
            self.session.add(result)
    
    def _import_space_noise_sources(self, sources: List[Dict]):
        """Import space noise sources"""
        for s_data in sources:
            source = SpaceNoiseSource(
                space_id=self._get_new_id('space', s_data['space_id']),
                name=s_data['name'],
                base_noise_dba=s_data.get('base_noise_dba'),
                distance_to_receiver_ft=s_data.get('distance_to_receiver_ft', 10.0),
                outlet_configuration=s_data.get('outlet_configuration', 'single'),
                num_outlets=s_data.get('num_outlets'),
            )
            self.session.add(source)

