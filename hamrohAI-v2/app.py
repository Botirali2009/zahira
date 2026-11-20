"""Hamroh — application factory.

`create_app()` loads config, runs migrations, registers blueprints and imports
the hook modules so their `@on(...)` decorators fire. Adding a hook means
adding a filename to HOOK_MODULES; adding an endpoint means adding a blueprint.
"""

import importlib
import logging
import os

from flask import Flask

from config import Config, features
from core import db
from core.errors import register_error_handlers
from core.responses import ok

# Extension modules imported for their side effects (decorator registration).
# A new hook/analyzer/notifier = a new file listed here, nothing else changes.
HOOK_MODULES = [
    "hooks.analysis_hooks",
    "hooks.alert_hooks",
    "hooks.call_hooks",
    "hooks.push_hooks",
    "hooks.medication_reminder_hooks",
    "hooks.motivation_hooks",
    "hooks.consultation_hooks",
]
# The "llm" analyzer slot has two interchangeable back ends — both register
# under the same name/priority (see analyzers/base.py), so exactly one of
# them may be imported at a time. Config.LLM_PROVIDER (env: LLM_PROVIDER)
# picks which; default is Anthropic, "gemini" switches to the free-tier
# alternative with no other code change.
_LLM_ANALYZER_MODULE = (
    "analyzers.gemini_analyzer" if Config.LLM_PROVIDER == "gemini"
    else "analyzers.llm_analyzer"
)
ANALYZER_MODULES = [
    "analyzers.rule_analyzer",
    _LLM_ANALYZER_MODULE,
]
NOTIFIER_MODULES = [
    "notifiers.in_app",
    "notifiers.call_notifier",
    "notifiers.push_notifier",
]
IDENTITY_PROVIDER_MODULES = [
    "identity_providers.google",
    "identity_providers.telegram",
    "identity_providers.dmed",
]

# (import path, url_prefix or None)
BLUEPRINTS = [
    ("routes.pages:bp", None),
    ("routes.auth_pages:bp", None),
    ("routes.doctor_profile_pages:bp", None),
    ("routes.doctor_patients_pages:bp", None),
    ("routes.patient_redeem_pages:bp", None),
    ("routes.patient_profile_pages:bp", None),
    ("routes.care_pages:bp", None),
    ("routes.consultation_pages:bp", None),
    ("routes.admin_pages:bp", None),
    ("routes.demo_api:bp", "/api/v1/demo"),
    ("routes.patient_api:bp", "/api/v1/patients"),
    ("routes.doctor_api:bp", "/api/v1/doctors"),
    ("routes.alert_api:bp", "/api/v1/alerts"),
    ("routes.call_api:bp", "/api/v1/patients"),
    ("routes.push_api:bp", "/api/v1/push"),
    ("routes.medication_api:bp", "/api/v1/care/patients"),
    ("routes.diagnosis_api:bp", "/api/v1/care/patients"),
    ("routes.trend_api:bp", "/api/v1/care/patients"),
    ("routes.diagnosis_files:bp", None),
]


def _load_modules(app, names, kind):
    for name in names:
        try:
            importlib.import_module(name)
            app.logger.info("%s loaded: %s", kind, name)
        except Exception:
            # A broken optional extension must not stop the app from starting.
            app.logger.exception("%s failed to load: %s", kind, name)


def _register_blueprints(app):
    for import_path, url_prefix in BLUEPRINTS:
        module_name, _, attr = import_path.rpartition(":")
        module = importlib.import_module(module_name)
        blueprint = getattr(module, attr)
        app.register_blueprint(blueprint, url_prefix=url_prefix)
        app.logger.info("blueprint registered: %s", import_path)


def _auto_ingest_guidelines(app):
    """Index any data/guidelines/*.txt file not already in guideline_chunks.

    Mirrors the migrations pattern (README: "no manual setup needed") — a
    fresh clone with source files already in data/guidelines/ just works.
    Runs once per file per source_name; editing a file's content in place
    doesn't get picked up until it's re-ingested (see scripts/ingest_guidelines.py)
    since there's no reliable "did the content change" check cheaper than
    just re-reading every file on every boot.
    """
    import glob
    import os as _os
    from repos import guideline_repo

    directory = app.config["GUIDELINES_DIR"]
    if not _os.path.isdir(directory):
        return
    existing = set(guideline_repo.sources())
    for path in sorted(glob.glob(_os.path.join(directory, "*.txt"))):
        source_name = _os.path.splitext(_os.path.basename(path))[0]
        if source_name in existing:
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            n = guideline_repo.ingest_text(source_name, text)
            app.logger.info("guideline ingested: %s (%d chunks)", source_name, n)
        except Exception:
            app.logger.exception("guideline ingest failed: %s", path)


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    # Allow a handful of documents per request without letting an upload run away.
    app.config["MAX_CONTENT_LENGTH"] = app.config["MAX_UPLOAD_SIZE_MB"] * 5 * 1024 * 1024

    logging.basicConfig(
        level=logging.DEBUG if app.config.get("DEBUG") else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    db.init_app(app)  # teardown + run_migrations()
    with app.app_context():
        _auto_ingest_guidelines(app)

    _load_modules(app, ANALYZER_MODULES, "analyzer")
    _load_modules(app, NOTIFIER_MODULES, "notifier")
    _load_modules(app, IDENTITY_PROVIDER_MODULES, "identity provider")
    _load_modules(app, HOOK_MODULES, "hook")

    _register_blueprints(app)
    register_error_handlers(app)

    @app.context_processor
    def inject_features():
        """Templates gate unfinished UI with features.enabled('...')."""
        return {"features": features}

    @app.get("/health")
    def health():
        return ok({
            "status": "ok",
            "db": app.config["DB_PATH"],
            "features": features.as_dict(),
        })

    return app


app = create_app()


if __name__ == "__main__":
    # Only the real dev server gets a background scheduler — importing this
    # module (tests, `flask shell`, etc.) never spawns a thread. In debug
    # mode Flask's reloader re-executes this block in a watcher process too;
    # WERKZEUG_RUN_MAIN is only set in the actual serving child, so this
    # guard keeps a second scheduler thread from racing the first.
    if not app.config["DEBUG"] or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        from services.medication_reminder_scheduler import start_background_thread
        start_background_thread(app)

    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
