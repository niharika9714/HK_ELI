# Deployment readiness

Local Windows/Mac setup is in the README. For a container, build with `docker build -f deployment/Containerfile -t hkeli-intelligence:local .`. The public image runs as a non-root UID and uses Waitress on port 8021. It does not contain the proprietary Stork SDK. Add its approved wheel during your controlled enterprise build; do not put credentials or private package-index tokens in image layers.

`deployment/openshift.yaml` is a reviewable single-replica template. Replace the example image reference, create a reviewed `hkeli-config` ConfigMap with `config.local.toml`, and provision `hkeli-runtime` using the cluster's approved secret-management process. Set `app.state_dir` to `/opt/hkeli/var`. Disable local test identity, use secure cookies and configure corporate SSO before exposing a Route. The app intentionally refuses the local demonstration login through the cluster Route.

The image declares port 8021, readiness/liveness endpoints, non-root execution, read-only root filesystem, dropped capabilities and resource limits. `/tmp` is an ephemeral bounded volume for CSV and rendering. Job/artifact state uses one ReadWriteOnce PVC and `Recreate` strategy. This template has not been deployed to your OpenShift cluster, and storage permissions/egress/CA/SSO/image policy require validation there.

Use **one replica and one application process**. SQLite startup recovery interrupts prior active jobs and is not a distributed work scheduler. Before scaling, replace SQLite state with an external transaction store, introduce a coordinated durable task queue, move protected artifacts to shared object storage and implement shared cancellation/locks/expiry. Do not increase replicas as a performance shortcut.

Run `python deployment/maintenance.py` on the single instance using the same config to delete expired draft files and terminal job records and retain thirty days of audit events. Expired reads are denied even before cleanup. Job TTL defaults to one hour and is measured from submission. At most sixteen active jobs and 255 prior terminal jobs are retained; individual result state is capped at two million characters. Tune storage/retention through approved change control.

Readiness checks only the local state database. Live Tableau, Stork and SPE health is deliberately not represented as healthy until an authenticated probe is designed for the environment. Use sanitized run trace exports and failure categories for diagnosis; do not enable raw SDK/request-body logs in production.

Chat history now also occupies the restricted state PVC: owned aggregate/evidence snapshots, not raw CSV/images or tokens. It defaults to a fixed 24-hour lifetime (`conversation_ttl_seconds`), at most 20 turns/8 million answer characters per chat and 20 chats per owner. Maintenance deletes expired history. Review this retention before real client use; see `CHAT_DOCUMENTS.md`. Persist a stable session secret if login cookies must survive application restarts.
