class PositionRepo(BaseRepo):
    async def create_position(self, position_data: dict) -> PositionModel:
        