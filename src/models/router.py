from pydantic import BaseModel, Field


class RouterOutput(BaseModel):
    datasets_to_query: list[str] = Field(
        description="Lista de datasets a consultar: 'df_metrics' y/o 'df_orders'"
    )
    reasoning: str = Field(
        description="Razón breve de por qué se seleccionaron estos datasets"
    )
