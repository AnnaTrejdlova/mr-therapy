from pydantic import BaseModel, Field
from typing import Union, Literal, Optional

class BaseGameSettings(BaseModel):
    difficulty: int = Field(
        default=1, ge=1, le=3,
        json_schema_extra={"ui_type": "slider", "label": "Obtížnost (Level)"}
    )
    iterations: int = Field(
        default=1, 
        ge=1, 
        le=3, 
        json_schema_extra={
            "ui_type": "slider", 
            "label": "Počet opakování (iterací)",
            "step": 1
        }
    )


class RotationCubeSettings(BaseGameSettings):
    game_type: Literal["rotation_cube"] = "rotation_cube"
    

class CorsiBlocksSettings(BaseGameSettings):
    game_type: Literal["corsi_blocks"] = "corsi_blocks"
    

class LocationRecallSettings(BaseGameSettings):
    game_type: Literal["location_recall"] = "location_recall"
    

class AttentionTrackingSettings(BaseGameSettings):
    game_type: Literal["attention_tracking"] = "attention_tracking"
    

class MrPuzzleSettings(BaseGameSettings):
    game_type: Literal["mr_puzzle"] = "mr_puzzle"


class CubeArcSettings(BaseGameSettings):
    game_type: Literal["cube_arc"] = "cube_arc"
    start_side: Literal["left", "right"] = Field(
        default="left",
        json_schema_extra={
            "ui_type": "select",
            "label": "Začít ze strany",
            "options": ["left", "right"],
        },
    )


# HLAVNÍ MODEL 
class GameCommand(BaseModel):
    payload: Union[
        RotationCubeSettings, 
        CorsiBlocksSettings, 
        LocationRecallSettings, 
        AttentionTrackingSettings,
        MrPuzzleSettings,
        CubeArcSettings
    ] = Field(..., discriminator="game_type")