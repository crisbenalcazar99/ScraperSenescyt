from typing import Optional, List, Dict, Type

from scraper_senescyt.utils.RunMode import RunMode
from scraper_senescyt.utils.general_functions import load_csv_file
from scraper_senescyt.utils.source_spec import SourceSpec


class PipelineConfig:
    def __init__(self, app_config):
        self.pipeline_name: str = "Scraper Supercias"
        self.mode_pipeline: RunMode = app_config.run_mode


class FeaturesFacturasExcluidasPipelines:
    def __init__(
            self,
            app_config: AppConfig,
            database_config: Optional[DatabaseConfig] = None,
            pipeline_config: Optional[PipelineConfig] = None
    ) -> None:
        self.database_config = database_config or DatabaseConfig(app_config)
        self.pipeline_config = pipeline_config or PipelineConfig(app_config)
        self.DATETIME_COLUMNS = ['creation_date', 'update_date']

    def _build_params_for_mode(self) -> Optional[dict[str, object]]:
        return None
        # Descomentar en caso de buscar una Act. incremental en funcion de un campo
        #     max_emission_date = DatabaseConfig.model_class.get_last_transaction_date(session)
        # return {"max_emission_date": max_emission_date}

    def _build_pipeline(self, spec: SourceSpec, sql_text: str, params: Optional[Dict[str, object]]) -> LoggingPipeline:
        is_initial = self.pipeline_config.mode_pipeline == RunMode.INICIAL
        steps = [

            extractor,
            # ('Transformation DateTime Dtype', DtypeDateTransform(self.DATETIME_COLUMNS)),
            ("Load DatawareHouse Bronze Articulos", DWBatchedLoader(
                db_alias=self.database_config.db_alias_load,
                model_class=self.database_config.model_class,
                mode=self.database_config.mode,
                conflict_cols=self.database_config.conflict_cols,
                update_cols=self.database_config.update_cols,
                commit_per_batch=self.database_config.commit_per_batch,
            ))

        ]
        return LoggingPipeline(steps, pipeline_name=self.pipeline_config.pipeline_name)

    def run(self):
        """
        Ejecuta el pipeline de integración en modo INICIAL o INCREMENTAL.
        """
        params = self._build_params_for_mode()

        # Construir y ejecutar un pipeline por Fuente
        for spec in self.pipeline_config.SOURCE_BY_MODE[self.pipeline_config.mode_pipeline]:
            # query = load_sql_statement(spec.folder_name, spec.query_file)
            pipe = self._build_pipeline(spec, query, params)
            pipe.fit_transform(None)
