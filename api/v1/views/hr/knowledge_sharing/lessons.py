from flask import Blueprint, request, jsonify, g, current_app
from api.v1.auth import login_required, role_required
from uuid import UUID
from api.v1.views import app_views
import traceback
from pydantic import ValidationError
from api.v1.services.hr.kss_services import (
    LessonCreateSchema, LessonUpdateSchema,
    EmployeeLessonProgressUpdateSchema, EmployeeLessonProgressCreateSchema
)

"""
endpoints for HR Manager to manage Knowledge Sharing System (KSS)
get create, update and delete module
get create, update and delete lesson
get create, update and delete assignment
get create, update and delete question
get create, update and delete employee lesson progress


The Idea
"""


@app_views.route('/kss/lessons', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin', 'employee', 'manager'])
def get_lessons():
    """Get all lessons"""
    try:
        lessons = g.supabase_user_client.from_('lessons').select('*').execute()
        return jsonify(lessons.data), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/kss/lessons/<uuid:lesson_id>', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin', 'employee', 'manager'])
def get_lesson(lesson_id):
    """Get a lesson by ID"""
    try:
        lesson_uuid = str(lesson_id)
        lesson = g.supabase_user_client.from_('lessons').select('*').eq('id', lesson_uuid).execute()
        if not lesson.data:
            return jsonify({"error": "Lesson not found"}), 404
        return jsonify(lesson.data[0]), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/kss/lessons', methods=['POST'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def create_lesson():
    try:
        data = request.get_json()
        validated_data = LessonCreateSchema(**data)
        lesson_data = validated_data.model_dump()
        created_lesson = g.supabase_user_client.from_('lessons').insert(lesson_data).execute()
        if not created_lesson.data:
            return jsonify({"error": "Failed to create lesson"}), 500
        print('created lesson ===== ', created_lesson)
        return jsonify(created_lesson.data[0]), 201
    
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/kss/lessons/<uuid:lesson_id>', methods=['PUT'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def update_lesson(lesson_id):
    try:
        data = request.get_json()
        validated_data = LessonUpdateSchema(**data)
        lesson_data = validated_data.model_dump(exclude_unset=True)
        lesson_uuid = str(lesson_id)

        updated_lesson = g.supabase_user_client.from_('lessons').update(lesson_data).eq('id', lesson_uuid).execute()
        if not updated_lesson.data:
            return jsonify({"error": "Lesson not found or no changes made"}), 404
        return jsonify(updated_lesson.data[0]), 200
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_views.route('/kss/lessons/<uuid:lesson_id>', methods=['DELETE'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def delete_lesson(lesson_id):
    try:
        lesson_uuid = str(lesson_id)
        deleted_lesson = g.supabase_user_client.from_('lessons').delete().eq('id', lesson_uuid).execute()
        if not deleted_lesson.data:
            return jsonify({"error": "Lesson not found"}), 404
        return jsonify({"message": "Lesson deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

