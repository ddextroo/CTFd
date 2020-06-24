from typing import List

from flask import request
from flask_restx import Namespace, Resource

from CTFd.api.v1.helpers.schemas import sqlalchemy_to_pydantic
from CTFd.api.v1.schemas import APIDetailedSuccessResponse, APIListSuccessResponse
from CTFd.cache import clear_config, clear_standings
from CTFd.models import Configs, db
from CTFd.schemas.config import ConfigSchema
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only

configs_namespace = Namespace("configs", description="Endpoint to retrieve Configs")

ConfigModel = sqlalchemy_to_pydantic(Configs)


class ConfigDetailedSuccessResponse(APIDetailedSuccessResponse):
    data: ConfigModel


class ConfigListSuccessResponse(APIListSuccessResponse):
    data: List[ConfigModel]


configs_namespace.schema_model(
    "ConfigDetailedSuccessResponse", ConfigDetailedSuccessResponse.apidoc()
)

configs_namespace.schema_model(
    "ConfigListSuccessResponse", ConfigListSuccessResponse.apidoc()
)


@configs_namespace.route("")
class ConfigList(Resource):
    @admins_only
    @configs_namespace.doc(
        description="Endpoint to get Config objects in bulk",
        responses={
            200: ("Success", "ConfigListSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    def get(self):
        configs = Configs.query.all()
        schema = ConfigSchema(many=True)
        response = schema.dump(configs)
        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}

    @admins_only
    @configs_namespace.doc(
        description="Endpoint to get create a Config object",
        responses={
            200: ("Success", "ConfigDetailedSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    def post(self):
        req = request.get_json()
        schema = ConfigSchema()
        response = schema.load(req)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        db.session.add(response.data)
        db.session.commit()

        response = schema.dump(response.data)
        db.session.close()

        clear_config()
        clear_standings()

        return {"success": True, "data": response.data}

    @admins_only
    @configs_namespace.doc(
        description="Endpoint to get patch Config objects in bulk",
        responses={200: ("Success", "APISimpleSuccessResponse")},
    )
    def patch(self):
        req = request.get_json()

        for key, value in req.items():
            set_config(key=key, value=value)

        clear_config()
        clear_standings()

        return {"success": True}


@configs_namespace.route("/<config_key>")
class Config(Resource):
    @admins_only
    # TODO: This returns weirdly structured data. It should more closely match ConfigDetailedSuccessResponse #1506
    def get(self, config_key):

        return {"success": True, "data": get_config(config_key)}

    @admins_only
    # TODO: This returns weirdly structured data. It should more closely match ConfigDetailedSuccessResponse #1506
    def patch(self, config_key):
        config = Configs.query.filter_by(key=config_key).first()
        data = request.get_json()
        if config:
            schema = ConfigSchema(instance=config, partial=True)
            response = schema.load(data)
        else:
            schema = ConfigSchema()
            data["key"] = config_key
            response = schema.load(data)
            db.session.add(response.data)

        if response.errors:
            return response.errors, 400

        db.session.commit()

        response = schema.dump(response.data)
        db.session.close()

        clear_config()
        clear_standings()

        return {"success": True, "data": response.data}

    @admins_only
    @configs_namespace.doc(
        description="Endpoint to delete a Config object",
        responses={200: ("Success", "APISimpleSuccessResponse")},
    )
    def delete(self, config_key):
        config = Configs.query.filter_by(key=config_key).first_or_404()

        db.session.delete(config)
        db.session.commit()
        db.session.close()

        clear_config()
        clear_standings()

        return {"success": True}
