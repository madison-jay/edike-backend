from flask import Blueprint, request, jsonify, g, current_app
from api.v1.auth import login_required, role_required
from uuid import UUID
from supabase import PostgrestAPIError
from api.v1.views import app_views
import traceback
from pydantic import ValidationError
from api.v1.services.hr.kss_services import (
    QuestionCreateSchema, QuestionUpdateSchema,
    EmployeeQuestionAnswerCreateSchema
)
from datetime import datetime


@app_views.route('/kss/questions/<uuid:module_id>', methods=['GET'])
@login_required
@role_required(['hr_manager', 'super_admin', 'user', 'manager'])
def get_questions(module_id):
    """fetch all questions by module id"""
    try:
        questions = g.supabase_user_client.from_('questions').select('*').eq('module_id', module_id).execute()
        if not questions.data:
            return [], 200
        return jsonify(questions.data), 200
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app_views.route('/kss/questions', methods=['POST'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def create_question():
    """Create a new question
    Expects JSON body with:
    - lesson_id: str
    - question_text: str
    - question_type: Literal['MULTIPLE_CHOICE', 'SHORT_ANSWER']
    - options: Dict[str, str]
    - correct_answer: str
    Returns the created question or error message
    """
    try:
        data = request.get_json()
        validated_data = QuestionCreateSchema(**data)
        question_data = validated_data.model_dump(exclude_unset=True)

        created_question = g.supabase_user_client.from_('questions').insert(question_data).execute()
        if not created_question.data:
            return jsonify({"error": "Failed to create question"}), 500
        return jsonify(created_question.data[0]), 201
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app_views.route('/kss/questions/<uuid:question_id>', methods=['PUT'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def update_question(question_id):
    """Update a question by ID
    Expects JSON body with any of the following fields:
    - question_text: Optional[str]
    - question_type: Optional[Literal['MULTIPLE_CHOICE', 'SHORT_ANSWER']]
    - options: Optional[Dict[str, str]]
    - correct_answer: Optional[str]
    Returns the updated question or error message
    """
    try:
        data = request.get_json()
        validated_data = QuestionUpdateSchema(**data)
        update_data = validated_data.model_dump(exclude_unset=True)
        question_uuid = str(question_id)

        existing_question = g.supabase_user_client.from_('questions').select('*').eq('id', question_uuid).execute()
        if not existing_question.data:
            return jsonify({"error": "Question not found"}), 404

        updated_question = g.supabase_user_client.from_('questions').update(update_data).eq('id', question_uuid).execute()
        if not updated_question.data:
            return jsonify({"error": "Failed to update question"}), 500

        return jsonify(updated_question.data[0]), 200
    
    except ValidationError as ve:
        current_app.logger.error(f"Validation error: {ve.errors()}")
        return jsonify({"error": ve.errors()}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@app_views.route('/kss/questions/<uuid:question_id>', methods=['DELETE'])
@login_required
@role_required(['hr_manager', 'super_admin'])
def delete_question(question_id):
    """Delete a question by ID"""
    try:
        question_uuid = str(question_id)
        existing_question = g.supabase_user_client.from_('questions').select('*').eq('id', question_uuid).execute()
        if not existing_question.data:
            return jsonify({"error": "Question not found"}), 404

        deleted_question = g.supabase_user_client.from_('questions').delete().eq('id', question_uuid).execute()
        if not deleted_question.data:
            return jsonify({"error": "Failed to delete question"}), 500

        return jsonify({"message": "Question deleted successfully"}), 200
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@app_views.route('/kss/test/submit', methods=['POST'])
@login_required
@role_required(['user', 'manager'])
def submit_question_answer():
    """Submit answers to questions. Expects JSON with employee_id, module_id, responses, and attempt_date."""
    # Validate input JSON
    data = request.get_json()
    if not data or not all(key in data for key in ['employee_id', 'module_id', 'responses']):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    employee_id = data['employee_id']
    module_id = data['module_id']
    responses = data['responses']
    attempt_date = data.get('attempt_date')
    if not attempt_date:
        attempt_date = datetime.utcnow().isoformat()

    if not all(
        isinstance(r, dict) and 'question_id' in r and 'submitted_answer' in r
        for r in responses
    ):
        return jsonify({"status": "error", "message": "Invalid response format"}), 400

    try:
        correct_answers_response = (
            g.supabase_user_client.from_('questions')
            .select('id, question_type, correct_answer')
            .eq('module_id', module_id)
            .execute()
        )

        if not correct_answers_response.data:
            return jsonify({"status": "error", "message": "No questions found for module"}), 404

        correct_answers = {q['id']: q['correct_answer'] for q in correct_answers_response.data}

        total_questions = len(correct_answers)
        correct_count = 0
        question_answer_records = []

        for response in responses:
            q_id = response['question_id']
            if q_id not in correct_answers:
                return jsonify({"status": "error", "message": f"Invalid question_id: {q_id}"}), 400

            submitted = str(response['submitted_answer']).strip()
            correct_answer = str(correct_answers[q_id]).strip()
            is_correct = submitted.lower() == correct_answer.lower()
            if is_correct:
                correct_count += 1

            answer_record = EmployeeQuestionAnswerCreateSchema(
                employee_id=employee_id,
                module_id=module_id,
                question_id=q_id,
                submitted_answer=submitted,
                is_correct=is_correct,
                attempt_date=attempt_date
            ).model_dump()

            question_answer_records.append(answer_record)

        # Calculate score and pass status 
        score_percentage = (correct_count / total_questions) * 100 if total_questions else 0
        passed = score_percentage >= 70.0


        g.supabase_user_client.table('employee_question_answers').insert(question_answer_records).execute()
        g.supabase_user_client.table('employee_test_results').upsert(
            {
                "employee_id": employee_id,
                "module_id": module_id,
                "score": round(score_percentage, 2),
                "passed": passed,
                "completion_date": attempt_date
            },
            on_conflict="employee_id,module_id"
        ).execute()

        return jsonify({
            "status": "success",
            "score": score_percentage,
            "passed": passed,
            "message": "Test results saved successfully"
        }), 200

    except PostgrestAPIError as e:
        current_app.logger.error(f"Supabase error: {str(e)}")
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500

@app_views.route('/kss/test/completion/<uuid:module_id>', methods=['GET'])
@login_required
@role_required(['user', 'manager', 'hr_manager', 'super_admin'])
def check_quiz_completion(module_id):
    """
    Check if the current user has completed (or attempted) a quiz for a module.
    Returns: score, passed, completion_date, or null if not taken.
    """
    try:
        # FIX: g.current_user is likely a string (user ID), not a dict
        employee_id = g.current_user
        if not employee_id:
            return jsonify({"status": "error", "message": "User ID not found"}), 400

        result = (
            g.supabase_user_client.table('employee_test_results')
            .select('score', 'passed', 'completion_date')
            .eq('employee_id', employee_id)
            .eq('module_id', str(module_id))
            .limit(1)
            .execute()
        )

        if result.data:
            return jsonify({
                "status": "success",
                "completed": True,
                "score": result.data[0]['score'],
                "passed": result.data[0]['passed'],
                "completion_date": result.data[0]['completion_date']
            }), 200
        else:
            return jsonify({
                "status": "success",
                "completed": False,
                "message": "Quiz not attempted"
            }), 200

    except PostgrestAPIError as e:
        current_app.logger.error(f"Supabase error: {str(e)}")
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500