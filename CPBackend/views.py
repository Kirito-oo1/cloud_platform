import json
import os
import re
from datetime import datetime
import subprocess
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


# 登录 API
@api_view(['POST'])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return Response({'message': 'Login successful'}, status=status.HTTP_200_OK)
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


# 任务规划 API
@api_view(['POST'])
def start_mission_planner(request):
    try:
        # 解析请求中的数据
        data = request.data

        # 获取无人设备数量
        drone_no = int(data.get('number_device', 0))

        # 获取扫描密度
        scanning_density = int(data.get('scan_density', 0))

        # 获取是否严格控制路径
        paths_strictly_in_poly = data.get('pathsStrictlyInPoly', False)

        # 获取任务区多边形
        mission_layer_point_arr = data.get('mission_layer_point_arr', [])
        polygon = [{"lat": point[1], "long": point[0]} for point in mission_layer_point_arr]

        # 获取障碍区多边形
        obstacle_layer_point_arr = data.get('obstacle_layer_point_arr', [])
        obstacles = [{"lat": point[1], "long": point[0]} for point in obstacle_layer_point_arr]

        # 获取出发点
        initial_pos = []
        for i in range(3):
            location_key = f'location{i + 1}'
            if location_key in data:
                location = data[location_key].split(",")
                initial_pos.append({
                    "lat": float(location[1]),
                    "long": float(location[0])
                })

        # 获取分配比例
        distribution_ratio1 = float(data.get('Distribution_ratio1', 0)) / 100
        distribution_ratio2 = float(data.get('Distribution_ratio2', 0)) / 100
        distribution_ratio3 = float(data.get('Distribution_ratio3', 0)) / 100
        r_portions = [distribution_ratio1, distribution_ratio2, distribution_ratio3]

        # 生成 JSON 文件
        mission_planner_file = {
            'droneNo': drone_no,
            'scanningDensity': scanning_density,
            'polygon': polygon,
            'obstacles': [obstacles],
            'pathsStrictlyInPoly': paths_strictly_in_poly,
            'initialPos': initial_pos,
            'rPortions': r_portions,
        }

        # 获取当前时间作为文件名
        out_file_date = datetime.now().strftime("%Y%m%d%H%M%S")

        # 使用相对路径生成文件路径
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前文件所在目录
        mission_planner_files_dir = os.path.join(base_dir, 'public', 'mission_planner_files')  # 获取相对目录
        os.makedirs(mission_planner_files_dir, exist_ok=True)  # 确保目录存在
        file_path = os.path.join(mission_planner_files_dir, f"{out_file_date}.json")

        # 将数据写入 JSON 文件
        try:
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(mission_planner_file, json_file, ensure_ascii=False, indent=2)
            print(f"JSON file written successfully: {file_path}")
        except Exception as e:
            print(f"Error writing JSON file: {e}")

        # Java 程序路径使用相对路径
        java_jar_path = os.path.join(base_dir, 'public', 'mcpp', 'mCPP-optimized-DARP.jar')

        # 执行 Java 程序
        java_command = f"java -jar {java_jar_path} {file_path}"
        result = subprocess.run(java_command, capture_output=True, text=True, shell=True)

        # 如果执行有错误
        if result.returncode != 0:
            return JsonResponse({"status": "error", "message": result.stderr},
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 处理 Java 程序的输出
        mission_route_result = text2arr(result.stdout)

        # 返回结果
        return JsonResponse({"status": "success", "result": mission_route_result}, status=status.HTTP_200_OK)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def text2arr(text):
    # 提取坐标的正则表达式
    regex = r"([\d.]+), ([\d.]+)"

    # 提取所有坐标
    coordinates = []
    matches = re.findall(regex, text)
    for match in matches:
        lat = float(match[0])
        lon = float(match[1])
        coordinates.append([lat, lon])

    # 提取各个无人机的 Waypoints 数量
    waypoints_counts = []
    waypoints_count_regex = r"Number of Waypoints for drone (\d+): (\d+)"
    waypoints_count_matches = re.findall(waypoints_count_regex, text)
    for waypoints_count_match in waypoints_count_matches:
        drone_index = int(waypoints_count_match[0])
        waypoints_count = int(waypoints_count_match[1])
        waypoints_counts.append(waypoints_count)

    # 根据 Waypoints 数量进行分割
    groups = []
    current_group = []
    current_index = 0
    for coordinate in coordinates:
        if len(current_group) >= waypoints_counts[current_index]:
            groups.append(current_group)
            current_group = []
            current_index += 1
        current_group.append(coordinate)

    # 添加最后一个分组
    if current_group:
        groups.append(current_group)

    return groups
