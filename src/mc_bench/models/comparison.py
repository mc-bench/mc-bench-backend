from sqlalchemy.orm import Mapped, relationship

import mc_bench.schema.postgres as schema
from mc_bench.models.model import Model
from mc_bench.models.prompt import Prompt, Tag
from mc_bench.models.run import Sample, TestSet

from ._base import Base


class Comparison(Base):
    __table__ = schema.scoring.comparison


class ComparisonRank(Base):
    __table__ = schema.scoring.comparison_rank


class ProcessedComparison(Base):
    __table__ = schema.scoring.processed_comparison


class Metric(Base):
    __table__ = schema.scoring.metric

    def to_dict(self):
        return {
            "id": self.external_id,
            "name": self.name,
            "description": self.description,
        }


class ModelLeaderboard(Base):
    __table__ = schema.scoring.model_leaderboard

    model: Mapped["Model"] = relationship("Model", uselist=False)  # type: ignore
    metric: Mapped["Metric"] = relationship("Metric", uselist=False)
    test_set: Mapped["TestSet"] = relationship("TestSet", uselist=False)
    tag: Mapped["Tag"] = relationship("Tag", uselist=False)  # type: ignore

    def to_dict(self, include_details=True):
        result = {
            "elo_score": self.elo_score,
            "vote_count": self.vote_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "tie_count": self.tie_count,
            "last_updated": self.last_updated,
        }

        if include_details:
            result.update(
                {
                    "model": self.model.to_dict() if self.model else None,
                    "metric": self.metric.to_dict() if self.metric else None,
                    "test_set": self.test_set.to_dict() if self.test_set else None,
                    "tag": self.tag.to_dict() if self.tag else None,
                }
            )
        else:
            result.update(
                {
                    "model_id": self.model_id,
                    "metric_id": self.metric_id,
                    "test_set_id": self.test_set_id,
                    "tag_id": self.tag_id,
                }
            )

        return result


class ModelGlickoLeaderboard(Base):
    __table__ = schema.scoring.model_glicko_leaderboard

    model: Mapped["Model"] = relationship("Model", uselist=False)  # type: ignore
    metric: Mapped["Metric"] = relationship("Metric", uselist=False)
    test_set: Mapped["TestSet"] = relationship("TestSet", uselist=False)
    tag: Mapped["Tag"] = relationship("Tag", uselist=False)  # type: ignore

    def to_dict(self, include_details=True):
        result = {
            "glicko_rating": self.glicko_rating,
            "rating_deviation": self.rating_deviation,
            "volatility": self.volatility,
            "vote_count": self.vote_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "tie_count": self.tie_count,
            "last_updated": self.last_updated,
        }

        if include_details:
            result.update(
                {
                    "model": self.model.to_dict() if self.model else None,
                    "metric": self.metric.to_dict() if self.metric else None,
                    "test_set": self.test_set.to_dict() if self.test_set else None,
                    "tag": self.tag.to_dict() if self.tag else None,
                }
            )
        else:
            result.update(
                {
                    "model_id": self.model_id,
                    "metric_id": self.metric_id,
                    "test_set_id": self.test_set_id,
                    "tag_id": self.tag_id,
                }
            )

        return result


class PromptLeaderboard(Base):
    __table__ = schema.scoring.prompt_leaderboard

    prompt: Mapped["Prompt"] = relationship("Prompt", uselist=False)
    model: Mapped["Model"] = relationship("Model", uselist=False)
    metric: Mapped["Metric"] = relationship("Metric", uselist=False)
    test_set: Mapped["TestSet"] = relationship("TestSet", uselist=False)
    tag: Mapped["Tag"] = relationship("Tag", uselist=False)  # type: ignore

    def to_dict(self, include_details=True):
        result = {
            "elo_score": self.elo_score,
            "vote_count": self.vote_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "tie_count": self.tie_count,
            "last_updated": self.last_updated,
        }

        if include_details:
            result.update(
                {
                    "prompt": self.prompt.to_dict() if self.prompt else None,
                    "model": self.model.to_dict() if self.model else None,
                    "metric": self.metric.to_dict() if self.metric else None,
                    "test_set": self.test_set.to_dict() if self.test_set else None,
                    "tag": self.tag.to_dict() if self.tag else None,
                }
            )
        else:
            result.update(
                {
                    "prompt_id": self.prompt_id,
                    "model_id": self.model_id,
                    "metric_id": self.metric_id,
                    "test_set_id": self.test_set_id,
                    "tag_id": self.tag_id,
                }
            )

        return result


class SampleLeaderboard(Base):
    __table__ = schema.scoring.sample_leaderboard

    sample: Mapped["Sample"] = relationship("Sample", uselist=False)
    metric: Mapped["Metric"] = relationship("Metric", uselist=False)
    test_set: Mapped["TestSet"] = relationship("TestSet", uselist=False)

    def to_dict(self, include_details=True):
        result = {
            "elo_score": self.elo_score,
            "vote_count": self.vote_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "tie_count": self.tie_count,
            "last_updated": self.last_updated,
        }

        if include_details:
            result.update(
                {
                    "sample": self.sample.to_dict(include_run=True)
                    if self.sample
                    else None,
                    "metric": self.metric.to_dict() if self.metric else None,
                    "test_set": self.test_set.to_dict() if self.test_set else None,
                }
            )
        else:
            result.update(
                {
                    "sample_id": self.sample_id,
                    "metric_id": self.metric_id,
                    "test_set_id": self.test_set_id,
                }
            )

        return result


__all__ = [
    "Comparison",
    "ComparisonRank",
    "Metric",
    "ModelLeaderboard",
    "ProcessedComparison",
    "PromptLeaderboard",
    "SampleLeaderboard",
    "ModelGlickoLeaderboard",
]
