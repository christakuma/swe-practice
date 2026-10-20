"""The quiz adapter: grade an answer sheet, running a fix question's tests.

Phase 25's engine. The choices are graded in `domain/quiz/`, which is where
the correctness-critical half lives; what is here is the half that needs a
process, and it borrows the kata runner rather than owning one, so this
package needs no entry in `test_architecture.py`'s lists.

* `grader.py`: `QuizGrader`, and `grade_sheet` for the content suite.
"""

from practice.adapters.quiz.grader import QuizGrader, QuizGraderError, grade_sheet

__all__ = ["QuizGrader", "QuizGraderError", "grade_sheet"]
