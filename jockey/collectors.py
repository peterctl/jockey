from typing import List
from jockey.types import Application, Machine, Unit


def get_machines(status: dict) -> List[Machine]:
    return [
        Machine(
            machine=m_id,
            hostname=m['hostname'],
            base=f"{m['base']['name']}:{m['base']['channel']}",
            hardware=m['hardware'],
        )
        for m_id, m in status.get('machines', {}).items()
    ]


def get_applications(status: dict) -> List[Application]:
    return [
        Application(
            app=a_id,
            charm=a['charm-name'],
            charm_rev=a['charm-rev'],
        )
        for a_id, a in status['applications'].items()
    ]


def get_units(status: dict) -> List[Unit]:
    result: List[Unit] = []
    for a_id, a in status.get('applications', {}).items():
        for u_id, u in status['applications'][a_id].get('units', {}).items():
            result.append(Unit(
                unit=u_id,
                machine=u['machine'],
                app=a_id,
                charm=a['charm'],
                workload=u['workload-status']['current'],
                agent=u['juju-status']['current'],
                ip=u['public-address'],
                leader=u['leader'],
                subordinate=False,
                subordinate_to=None,
            ))
            for s_id, s in u.get('subordinates', {}).items():
                s_app, _ = s_id.split('/')
                result.append(Unit(
                    unit=s_id,
                    machine=u['machine'],
                    app=s_app,
                    charm=status['applications'][s_app]['charm-name'],
                    workload=s['workload-status']['current'],
                    agent=s['juju-status']['current'],
                    ip=s['public-address'],
                    leader=s['leader'],
                    subordinate=True,
                    subordinate_to=u_id,
                ))
    return result

