from typing import List
from jockey.juju_types import Application, Machine, Unit


def get_machines(status: dict) -> List[Machine]:
    result: List[Machine] = []
    for m_id, m in status.get('machines', {}).items():
        result.append(Machine(
            machine=m_id,
            hostname=m['hostname'],
            base=m['series'] if 'series' in m else f"{m['base']['name']}:{m['base']['channel']}",
            hardware=m['hardware'],
        ))
        for c_id, c in m.get('containers', {}).items():
            result.append(Machine(
                machine=c_id,
                hostname=c['hostname'],
                base=c['series'] if 'series' in c else f"{c['base']['name']}:{c['base']['channel']}",
                hardware=c['hardware'],
            ))
    return result


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
    machines = get_machines(status)
    m_map = {
        m.machine: m for m in machines
    }

    result: List[Unit] = []
    for a_id, a in status.get('applications', {}).items():
        for u_id, u in status['applications'][a_id].get('units', {}).items():
            result.append(Unit(
                unit=u_id,
                machine=u['machine'],
                hostname=m_map[u['machine']].hostname,
                app=a_id,
                charm=a['charm'],
                workload=u['workload-status']['current'],
                agent=u['juju-status']['current'],
                ip=u['public-address'],
                leader=u.get('leader', False),
                subordinate=False,
                subordinate_to=None,
            ))
            for s_id, s in u.get('subordinates', {}).items():
                s_app, _ = s_id.split('/')
                result.append(Unit(
                    unit=s_id,
                    machine=u['machine'],
                    hostname=m_map[u['machine']].hostname,
                    app=s_app,
                    charm=status['applications'][s_app]['charm-name'],
                    workload=s['workload-status']['current'],
                    agent=s['juju-status']['current'],
                    ip=s['public-address'],
                    leader=s.get('leader', False),
                    subordinate=True,
                    subordinate_to=u_id,
                ))
    return result

