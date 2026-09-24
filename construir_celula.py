#!/usr/bin/env python3
"""Create the portfolio polishing cell in a running, local RoboDK instance.

Only simulation is used. Each run creates a new station, preserving existing ones.
Run: /usr/bin/python3 construir_celula.py
"""
from pathlib import Path
import json
import math
import sys

ROOT = Path(__file__).resolve().parent
API = Path.home() / '.local/share/robodk/Python'
if API.exists():
    sys.path.insert(0, str(API))
from robodk.robolink import (
    Robolink, ITEM_TYPE_FRAME, COLLISION_ON, COLLISION_OFF,
    RUNMODE_SIMULATE, PROGRAM_RUN_ON_SIMULATOR, PROJECTION_NONE,
    VISIBLE_ROBOT_DEFAULT, VISIBLE_ROBOT_ALL_REFS,
)
from robodk.robomath import Mat, transl, rotx, roty, invH, eye

RADIUS = 40.0
TOOL_LENGTH = 200.0
WORK_ORIGIN = [850.0, 0.0, 590.0]
# This library model places its kinematic origin 450 mm above its mounting face.
ROBOT_ORIGIN = [0.0, 0.0, 500.0]


def box(cx, cy, cz, sx, sy, sz):
    vertices = [[cx+dx*sx/2, cy+dy*sy/2, cz+dz*sz/2]
                for dx, dy, dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                   (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    faces = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
             (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return [vertices[i] for face in faces for i in face]


def cylinder(radius, z0, z1, segments=48):
    pts = []
    for i in range(segments):
        a, b = 2*math.pi*i/segments, 2*math.pi*(i+1)/segments
        p = [radius*math.cos(a), radius*math.sin(a), z0]
        q = [radius*math.cos(b), radius*math.sin(b), z0]
        r, s = [q[0],q[1],z1], [p[0],p[1],z1]
        pts += [[0,0,z0],q,p, [0,0,z1],s,r, p,q,r, p,r,s]
    return pts


def surface_z(x):
    return 30.0 - 4.0*(x/150.0)**2


def part_mesh():
    pts = []
    for i in range(60):
        a, b = -150+i*5, -150+(i+1)*5
        p,q,r,s = [a,-100,surface_z(a)],[b,-100,surface_z(b)], [b,100,surface_z(b)],[a,100,surface_z(a)]
        pts += [p,q,r,p,r,s]
        for y, reverse in [(-100,False),(100,True)]:
            v = [[a,y,0],[b,y,0],[b,y,surface_z(b)],[a,y,surface_z(a)]]
            order = [0,1,2,0,2,3] if not reverse else [0,2,1,0,3,2]
            pts += [v[j] for j in order]
    for x, reverse in [(-150,True),(150,False)]:
        v = [[x,-100,0],[x,100,0],[x,100,surface_z(x)],[x,-100,surface_z(x)]]
        order = [0,1,2,0,2,3] if not reverse else [0,2,1,0,3,2]
        pts += [v[j] for j in order]
    pts += [[-150,-100,0],[-150,100,0],[150,100,0],[-150,-100,0],[150,100,0],[150,-100,0]]
    return pts


def save_stl(path, triangles):
    # ASCII STL retained for editing/reuse outside the station.
    with path.open('w') as f:
        f.write('solid tampa_aluminio\n')
        for i in range(0,len(triangles),3):
            f.write(' facet normal 0 0 0\n  outer loop\n')
            for p in triangles[i:i+3]:
                f.write('   vertex %g %g %g\n' % tuple(p))
            f.write('  endloop\n endfacet\n')
        f.write('endsolid tampa_aluminio\n')


def contact_pose(x,y,lift=0):
    slope = -8*x/22500.0
    return transl(x,y,surface_z(x)+lift)*roty(-math.atan(slope))*rotx(math.pi)


def view_pose(eye_pt, target):
    def norm(v):
        length = math.sqrt(sum(x*x for x in v))
        return [x/length for x in v]
    def cross(a,b):
        return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    z = norm([a-b for a,b in zip(eye_pt,target)])
    x = norm(cross([0,0,1],z))
    y = cross(z,x)
    camera = Mat([[x[i],y[i],z[i],eye_pt[i]] for i in range(3)]+[[0,0,0,1]])
    return invH(camera)


def main():
    rdk = Robolink(robodk_ip='127.0.0.1',port=20500,quit_on_close=False)
    rdk.setRunMode(RUNMODE_SIMULATE)
    station = rdk.AddStation('FANUC | Polimento de tampa em aluminio')
    rdk.Render(False)
    try:
        layout = rdk.AddFrame('01 | Estrutura da celula',station)
        robot_base = rdk.AddFrame('02 | Base FANUC',station)
        robot_base.setPose(transl(*ROBOT_ORIGIN))
        work = rdk.AddFrame('03 | Peca - UFRAME 1',station)
        work.setPose(transl(*WORK_ORIGIN))

        def shape(name, points, color, parent=layout):
            obj = rdk.AddShape(Mat(points).tr())
            obj.setName(name)
            obj.setParent(parent)
            obj.setPose(eye(4))
            obj.setColor(color)
            obj.setVisible(True,False)
            return obj

        dark = [0.13,0.17,0.22,1]
        steel = [0.40,0.46,0.53,1]
        yellow = [1.0,0.69,0.03,1]
        shape('Plataforma',box(400,0,-35,2100,1700,60),dark)
        marking=[]
        for y in [-795,795]: marking += box(400,y,-3,2000,12,3)
        for x in [-595,1395]: marking += box(x,0,-3,12,1590,3)
        shape('Delimitacao amarela',marking,yellow)
        shape('Placa de montagem do robo',box(0,0,25,380,380,50),steel)
        shape('Mesa - tampo',box(850,0,545,560,500,30),steel)
        legs=[]
        for x in [630,1070]:
            for y in [-190,190]:
                legs += box(x,y,265,50,50,530)+box(x,y,12,95,95,24)
        legs += box(850,190,150,440,30,40)+box(850,-190,150,440,30,40)
        shape('Mesa - estrutura',legs,dark)
        shape('Base de fixacao',box(850,0,570,380,300,20),[0.20,0.28,0.36,1])
        supports=box(850,-60,585,240,30,10)+box(850,60,585,240,30,10)
        shape('Apoios da peca',supports,steel)
        # Low side stops remain below the swept polishing pad.
        stops=[]
        for y in [-106,106]: stops += box(850,y,587,240,12,14)
        shape('Batentes laterais',stops,[0.07,0.49,0.58,1])
        piece = shape('Tampa aluminio 300 x 200 x 30',part_mesh(),[0.78,0.83,0.88,1],work)
        save_stl(ROOT/'assets/tampa_aluminio.stl',part_mesh())

        # Three-sided concept guard: open front keeps the demonstration legible.
        guard=[]
        for x in [-550,400,1350]: guard += box(x,740,750,35,35,1500)
        for x in [-550,1350]: guard += box(x,-350,750,35,35,1500)
        for z in [80,1500]:
            guard += box(400,740,z,1935,30,30)
            for x in [-550,1350]: guard += box(x,195,z,30,1090,30)
        shape('Protecao - estrutura conceptual',guard,yellow)
        mesh=[]
        for x in range(-500,1350,100): mesh += box(x,740,790,3,3,1400)
        for z in range(100,1500,100): mesh += box(400,740,z,1900,3,3)
        for x in [-550,1350]:
            for y in range(-300,740,100): mesh += box(x,y,790,3,3,1400)
            for z in range(100,1500,100): mesh += box(x,195,z,3,1090,3)
        shape('Protecao - malha',mesh,[0.22,0.26,0.30,1])

        robot = rdk.AddFile(str(ROOT/'assets/Fanuc-M-10iD-12.robot'),robot_base)
        # The library file embeds its own base frame and demonstration offset.
        if robot.Parent().item != robot_base.item:
            robot.Parent().setPose(eye(4))
            robot.Parent().setVisible(False)
        robot.setName('FANUC M-10iD/12')
        robot.setParam('PostProcessor','Fanuc_R30i')
        tool_pose = transl(0,0,TOOL_LENGTH)
        tool = robot.AddTool(tool_pose,'Polidora D80 - TCP 1')
        # Tool mesh coordinates are relative to the robot flange.
        rdk.AddShape([Mat(cylinder(32,0,14)).tr(),steel,
                      Mat(cylinder(26,14,153)).tr(),[0.07,0.49,0.58,1],
                      Mat(cylinder(14,153,185)).tr(),steel,
                      Mat(cylinder(RADIUS,185,197)).tr(),dark,
                      Mat(cylinder(RADIUS,197,200)).tr(),[0.77,0.41,0.13,1]],tool)
        tool.setVisible(True,False)
        robot.setPoseTool(tool)
        robot.setPoseFrame(work)
        rdk.Update()
        reference = invH(robot.PoseAbs())*work.PoseAbs()
        seed = [0,0,0,0,-90,0]
        target_joints={}

        def target(name,pose,joint=False):
            nonlocal seed
            joints=robot.SolveIK(pose,seed,tool_pose,reference).tolist()
            if len(joints)<6:
                raise RuntimeError('Unreachable target: '+name+'; reference='+str(reference)+'; seed='+str(seed))
            joints=joints[:6]
            seed=joints
            item=rdk.AddTarget(name,work,robot)
            item.setPose(pose)
            item.setJoints(joints)
            if joint: item.setAsJointTarget()
            else: item.setAsCartesianTarget()
            item.setVisible(False)
            target_joints[name]=joints
            return item

        home=target('HOME',contact_pose(-130,-80,220),True)
        approach=target('APROXIMACAO',contact_pose(-130,-80,80))
        passes=[]
        path_points=[]
        for row,y in enumerate([-80,-40,0,40,80]):
            xs=[-130,-65,0,65,130]
            if row%2: xs.reverse()
            line=[]
            for col,x in enumerate(xs):
                line.append(target('P%d_%d'%(row+1,col+1),contact_pose(x,y)))
                path_points.append([x,y,surface_z(x)+1.0])
            passes.append(line)
        retract=target('AFASTAMENTO',contact_pose(130,80,80))
        curve=rdk.AddCurve(Mat(path_points).tr(),projection_type=PROJECTION_NONE)
        curve.setParent(work)
        curve.setPose(eye(4))
        curve.setName('Percurso de polimento - 5 passagens')
        curve.setColorCurve([0.02,0.75,0.85,1])
        curve.setValue('Display','LINEW=3')
        curve.setVisible(True,False)

        prog=rdk.AddProgram('POLIR',robot)
        prog.setRunType(PROGRAM_RUN_ON_SIMULATOR)
        prog.setPoseFrame(work)
        prog.setPoseTool(tool)
        prog.setRounding(1)
        prog.setSpeed(100,30,250,60)
        prog.MoveJ(home)
        prog.MoveJ(approach)
        prog.setDO(1,1)
        prog.setSpeed(40)
        for line in passes:
            for item in line: prog.MoveL(item)
        prog.MoveL(retract)
        prog.setDO(1,0)
        prog.setSpeed(100)
        prog.MoveJ(home)
        prog.ShowTargets(False)
        prog.ShowInstructions(True)
        count=prog.InstructionCount()
        if count>45:
            raise RuntimeError('Program exceeds the conservative 45-instruction budget')
        robot.setJoints(target_joints['HOME'])
        rdk.setSimulationSpeed(1)
        rdk.Render(True)
        # Validate the complete interpolated trajectory; intentional pad/part
        # contact is excluded, while robot links, fixture and guards are checked.
        rdk.setCollisionActive(COLLISION_ON)
        rdk.setCollisionActivePair(COLLISION_OFF,tool,piece)
        rdk.setCollisionActivePair(COLLISION_OFF,robot,tool,6,0)
        result=prog.Update(COLLISION_ON,timeout_sec=60,mm_step=5,deg_step=3)
        report={
            'robodk_version':rdk.Version(),
            'license':rdk.License()[0],
            'program':'POLIR','instructions':count,
            'passes':5,'points_per_pass':5,'pad_diameter_mm':80,
            'feed_mm_s':40,'overlap_percent':50,
            'validation':{'valid_instructions':result[0],'estimated_seconds':result[1],
                          'distance_mm':result[2],'valid_ratio':result[3],'message':result[4]},
            'collision_sampling':{'mm_step':5,'deg_step':3,'excluded_pairs':['polishing pad/tool and workpiece (intended contact)','robot flange (link 6) and attached tool (mounting contact)']},
            'scope':'Geometric and kinematic simulation; finish, contact force and production safety are not validated.',
        }
        (ROOT/'verificacao.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        if result[3]<1.0:
            rdk.Save(str(ROOT/'celula_em_revisao.rdk'),station)
            raise RuntimeError('Trajectory validation incomplete: '+str(result))
        robot.setJoints(target_joints['HOME'])
        for frame in [layout,robot_base,work]: frame.setVisible(False)
        robot.setVisible(True,VISIBLE_ROBOT_DEFAULT & ~VISIBLE_ROBOT_ALL_REFS)
        prog.setVisible(False)
        prog.setParam('Tree','Collapse')
        rdk.setSelection([])
        layout.setParam('Tree','Collapse')
        robot_base.setParam('Tree','Expand')
        work.setParam('Tree','Collapse')
        rdk.setViewPose(view_pose([2550,-3000,2350],[430,0,650]))
        rdk.Command('FitAll')
        rdk.Save(str(ROOT/'Celula_Polimento_FANUC.rdk'),station)
        rdk.Cam2D_Snapshot(str(ROOT/'vista_celula.png'),None)
        print(json.dumps(report,indent=2,ensure_ascii=False),flush=True)
        print('Saved:',ROOT/'Celula_Polimento_FANUC.rdk',flush=True)
    finally:
        rdk.Render(True)
        rdk.Disconnect()


if __name__=='__main__':
    main()
