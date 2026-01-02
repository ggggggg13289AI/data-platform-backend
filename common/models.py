"""
Common Models - Shared models across modules.
"""

import uuid

from django.conf import settings
from django.db import models


class StudyProjectAssignment(models.Model):
    """研究-專案分配模型"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    project = models.ForeignKey(
        "project.Project",
        on_delete=models.CASCADE,
        related_name="study_assignments",
        verbose_name="專案",
    )
    study = models.ForeignKey(
        "study.Study",
        to_field="exam_id",
        on_delete=models.CASCADE,
        related_name="project_assignments",
        verbose_name="研究",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="study_assignments",
        verbose_name="分配者",
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="分配時間",
    )
    metadata = models.JSONField(
        default=dict,
        verbose_name="元數據",
    )

    class Meta:
        app_label = "common"
        db_table = "study_project_assignments"
        verbose_name = "研究分配"
        verbose_name_plural = "研究分配"
        unique_together = [["project", "study"]]
        ordering = ["project", "-assigned_at"]
        indexes = [
            models.Index(
                fields=["project", "-assigned_at"],
                name="idx_spa_proj_assigned",
            ),
            models.Index(
                fields=["study", "project"],
                name="idx_spa_study_proj",
            ),
            models.Index(
                fields=["assigned_by"],
                name="idx_spa_assigned_by",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.study_id} → {self.project.name}"

    def to_dict(self) -> dict:
        """轉換為字典格式"""
        assigned_by = self.assigned_by
        return {
            "id": str(self.id),
            "project_id": str(self.project.id),
            "study_id": self.study_id,
            "assigned_by": {
                "id": str(assigned_by.id),
                "name": assigned_by.get_full_name() or assigned_by.get_username(),
                "email": assigned_by.email,
            },
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "metadata": self.metadata,
        }
