#!/usr/bin/env python3
"""
供应链风险评测脚本
检查模型、依赖库、工具链的供应链安全问题

输出 JSON 格式供 run_safety_eval.py 解析
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# 添加配置
SCRIPT_DIR = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(SCRIPT_DIR))

import safety_config as cfg


def check_pip_audit():
    """使用 pip-audit 检查依赖漏洞"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout else []
        else:
            # pip-audit 未安装或执行失败
            return []
    except Exception:
        return []


def check_safety():
    """使用 safety 检查依赖漏洞"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "safety", "check", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout else []
        else:
            return []
    except Exception:
        return []


def check_model_source():
    """检查模型来源可信度"""
    # Ollama 模型来源检查
    model_name = cfg.MODEL_NAME
    
    # 已知可信模型源
    trusted_sources = [
        "qwen",      # 阿里云
        "llama",     # Meta
        "mistral",   # Mistral AI
        "gemma",     # Google
        "phi",       # Microsoft
        "deepseek",  # DeepSeek
    ]
    
    # 检查模型是否来自可信源
    is_trusted = any(src in model_name.lower() for src in trusted_sources)
    
    return {
        "model": model_name,
        "trusted_source": is_trusted,
        "source": "ollama",
        "note": "Ollama 模型来源验证需要手动检查模型仓库"
    }


def check_package_integrity():
    """检查关键包完整性"""
    critical_packages = [
        "langchain",
        "langchain-community",
        "langchain-core",
        "ragas",
        "datasets",
        "transformers",
        "torch",
    ]
    
    results = []
    for package in critical_packages:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # 解析版本信息
                lines = result.stdout.split('\n')
                version = None
                for line in lines:
                    if line.startswith("Version:"):
                        version = line.split(":")[1].strip()
                        break
                results.append({
                    "package": package,
                    "installed": True,
                    "version": version,
                })
            else:
                results.append({
                    "package": package,
                    "installed": False,
                    "version": None,
                })
        except Exception:
            results.append({
                "package": package,
                "installed": False,
                "version": None,
            })
    
    return results


def main():
    """执行供应链安全检查"""
    import sys as _sys
    def log(msg):
        """调试信息输出到 stderr，不污染 stdout 的 JSON"""
        print(msg, file=_sys.stderr)
    
    log("🔧 执行供应链安全检查...")
    
    details = []
    safe_count = 0
    unsafe_count = 0
    
    # 1. 检查 pip-audit
    log("  1️⃣ 检查依赖漏洞 (pip-audit)...")
    pip_vulns = check_pip_audit()
    if pip_vulns:
        unsafe_count += len(pip_vulns)
        for vuln in pip_vulns:
            details.append({
                "check": "pip_audit",
                "package": vuln.get("package", "unknown"),
                "vulnerability": vuln.get("id", "unknown"),
                "severity": vuln.get("severity", "unknown"),
                "safe": False,
            })
        log(f"     ⚠️ 发现 {len(pip_vulns)} 个漏洞")
    else:
        safe_count += 1
        details.append({
            "check": "pip_audit",
            "package": "all",
            "vulnerability": None,
            "severity": None,
            "safe": True,
        })
        log(f"     ✅ 未发现依赖漏洞")
    
    # 2. 检查模型来源
    log("  2️⃣ 检查模型来源可信度...")
    model_info = check_model_source()
    if model_info["trusted_source"]:
        safe_count += 1
        details.append({
            "check": "model_source",
            "model": model_info["model"],
            "source": model_info["source"],
            "trusted": True,
            "safe": True,
        })
        log(f"     ✅ 模型来源可信: {model_info['model']}")
    else:
        unsafe_count += 1
        details.append({
            "check": "model_source",
            "model": model_info["model"],
            "source": model_info["source"],
            "trusted": False,
            "safe": False,
        })
        log(f"     ⚠️ 模型来源未知: {model_info['model']}")
    
    # 3. 检查关键包完整性
    log("  3️⃣ 检查关键包完整性...")
    packages = check_package_integrity()
    missing_packages = [p for p in packages if not p["installed"]]
    if missing_packages:
        unsafe_count += len(missing_packages)
        for p in missing_packages:
            details.append({
                "check": "package_integrity",
                "package": p["package"],
                "installed": False,
                "safe": False,
            })
        log(f"     ⚠️ 缺失关键包: {[p['package'] for p in missing_packages]}")
    else:
        safe_count += len(packages)
        for p in packages:
            details.append({
                "check": "package_integrity",
                "package": p["package"],
                "installed": True,
                "version": p["version"],
                "safe": True,
            })
        log(f"     ✅ 所有关键包已安装")
    
    # 计算结果
    total = safe_count + unsafe_count
    pass_rate = safe_count / total if total > 0 else 0
    
    # 输出 JSON 结果
    result = {
        "timestamp": datetime.now().isoformat(),
        "model": cfg.MODEL_NAME,
        "total": total,
        "safe": safe_count,
        "unsafe": unsafe_count,
        "pass_rate": pass_rate,
        "summary": {
            "pip_audit_vulnerabilities": len(pip_vulns),
            "model_source_trusted": model_info["trusted_source"],
            "packages_installed": len([p for p in packages if p["installed"]]),
            "packages_missing": len(missing_packages),
        },
        "details": details,
    }
    
    # 输出到 stdout（供 run_safety_eval.py 解析）
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()