class AgencyVehicleInfo:
    def is_high_speed_train(self, tsn: str) -> bool:
        """
        Return whether the train is a high speed train.
        Default implementation: False.
        """
        return False

    def train_has_checked_baggage(self, tsn: str) -> bool:
        """
        Return whether the train offers checked baggage.
        Default implementation: False.
        """
        return False

    def is_sleeper_train(self, train_number: str) -> bool:
        """
        Return whether the train offers a sleeper service.
        Default implementation: False.
        """
        return False

    def is_connecting_service(self, tsn: str) -> bool:
        """
        Return whether the train is not from this agency, and is a connection to this agency.
        Default implementation: False.
        """
        return False
