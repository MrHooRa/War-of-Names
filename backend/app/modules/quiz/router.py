"""Quiz session endpoints — get active quiz, submit answers, earn rewards."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import (
    AnswerEvalStatus,
    LedgerDirection,
    LedgerEntryType,
    MembershipStatus,
    NotificationType,
    SessionStatus,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import Membership
from app.modules.notifications.service import create_notification
from app.modules.quiz.models import AnswerSubmission, QuizSession, SessionQuestion
from app.modules.scoring.models import LedgerEntry

router = APIRouter(tags=["quiz"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


class SubmitAnswerRequest(BaseModel):
    session_question_id: uuid.UUID
    answer: str


@router.get("/api/quiz/active")
async def get_active_quiz(account: CurrentAccount):
    """Get the currently open quiz session with its questions (no correct answers)."""
    async with async_session() as session:
        # Find user's active membership
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
            ).limit(1)
        )
        membership = mem_result.scalars().first()
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في أي منافسة")

        # Find open quiz session for this competition
        quiz_result = await session.execute(
            select(QuizSession).where(
                QuizSession.competition_id == membership.competition_id,
                QuizSession.status == SessionStatus.OPEN,
            ).limit(1)
        )
        quiz = quiz_result.scalars().first()
        if not quiz:
            return {"success": True, "data": None, "message": "لا توجد جلسة أسئلة نشطة حالياً"}

        # Get session questions
        sq_result = await session.execute(
            select(SessionQuestion)
            .where(SessionQuestion.session_id == quiz.id)
            .order_by(SessionQuestion.delivery_order)
        )
        session_questions = sq_result.scalars().all()

        # Get already-answered questions
        ans_result = await session.execute(
            select(AnswerSubmission.session_question_id).where(
                AnswerSubmission.membership_id == membership.id,
                AnswerSubmission.session_id == quiz.id,
            )
        )
        answered_ids = {row[0] for row in ans_result.all()}

    questions = []
    for sq in session_questions:
        options = sq.effective_options_snapshot or {}
        questions.append({
            "session_question_id": str(sq.id),
            "question_number": sq.delivery_order,
            "prompt": sq.effective_prompt_snapshot,
            "options": options.get("choices", []),
            "score_value": sq.effective_score_value,
            "already_answered": sq.id in answered_ids,
        })

    return {
        "success": True,
        "data": {
            "session_id": str(quiz.id),
            "title": quiz.title,
            "total_questions": len(questions),
            "answer_duration_seconds": quiz.answer_duration_seconds,
            "questions": questions,
        },
    }


@router.post("/api/quiz/{session_id}/answer")
async def submit_answer(
    session_id: uuid.UUID,
    body: SubmitAnswerRequest,
    account: CurrentAccount,
):
    """Submit an answer to a quiz question. Returns correctness and points awarded."""
    async with async_session() as session:
        # Get membership
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
            ).limit(1)
        )
        membership = mem_result.scalars().first()
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في أي منافسة")

        # Verify quiz session
        quiz = await session.get(QuizSession, session_id)
        if not quiz or quiz.status != SessionStatus.OPEN:
            raise HTTPException(status_code=400, detail="جلسة الأسئلة غير متاحة")

        # Get session question
        sq = await session.get(SessionQuestion, body.session_question_id)
        if not sq or str(sq.session_id) != str(session_id):
            raise HTTPException(status_code=404, detail="السؤال غير موجود في هذه الجلسة")

        # Check if already answered
        existing = await session.execute(
            select(AnswerSubmission).where(
                AnswerSubmission.membership_id == membership.id,
                AnswerSubmission.session_question_id == sq.id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="لقد أجبت على هذا السؤال مسبقاً")

        # Evaluate answer
        correct_answer = sq.effective_options_snapshot.get("correct", "")
        is_correct = body.answer.strip() == str(correct_answer).strip()
        points = sq.effective_score_value if is_correct else 0

        # Create answer submission
        submission = AnswerSubmission(
            membership_id=membership.id,
            session_id=session_id,
            session_question_id=sq.id,
            submitted_answer={"answer": body.answer},
            status=AnswerEvalStatus.EVALUATED,
            is_correct=is_correct,
            points_awarded=points,
            evaluated_at=datetime.utcnow(),
        )
        session.add(submission)

        # Award points via ledger if correct
        balance_after = membership.current_balance
        if is_correct and points > 0:
            balance_before = membership.current_balance
            balance_after = balance_before + points

            ledger = LedgerEntry(
                membership_id=membership.id,
                competition_id=membership.competition_id,
                entry_type=LedgerEntryType.QUESTION_REWARD,
                amount=points,
                direction=LedgerDirection.CREDIT,
                balance_before=balance_before,
                balance_after=balance_after,
                source_type="answer_submission",
                reason=f"إجابة صحيحة على سؤال في الجلسة",
            )
            session.add(ledger)
            membership.current_balance = balance_after

        # Notification for correct answers
        if is_correct and points > 0:
            await create_notification(
                session,
                recipient_id=account.id,
                notification_type=NotificationType.QUIZ_OPENED,
                title="إجابة صحيحة!",
                message=f"حصلت على {points} نقطة من جلسة الأسئلة",
                membership_id=membership.id,
                reference_type="quiz_session",
                reference_id=session_id,
                deep_link="/quiz",
            )

        await session.commit()

    return {
        "success": True,
        "data": {
            "is_correct": is_correct,
            "correct_answer": str(correct_answer),
            "points_awarded": points,
            "balance_after": balance_after,
        },
        "message": f"إجابة صحيحة! +{points} نقطة" if is_correct else "إجابة خاطئة!",
    }
