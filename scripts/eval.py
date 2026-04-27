import json
import sys
import os
from collections import defaultdict

# Add app to path to import classifier
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.profiling.classifier import RuleBasedClassifier

def run_eval(dataset_path: str):
    with open(dataset_path, 'r') as f:
        data = json.load(f)
        
    traders_data = data.get('traders', []) if isinstance(data, dict) else data
        
    pathologies = [
        "revenge_trading", "overtrading", "fomo_entries", "plan_non_adherence",
        "premature_exit", "loss_running", "session_tilt", "time_of_day_bias",
        "position_sizing_inconsistency"
    ]
    
    # Initialize metrics structure
    metrics = {
        "perClass": {p: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for p in pathologies},
        "perTrader": []
    }
    
    for trader in traders_data:
        user_id = trader.get('userId')
        name = trader.get('name')
        gt_pathologies_raw = trader.get('groundTruthPathologies', [])
        gt_pathologies = []
        for p in gt_pathologies_raw:
            # Normalize to snake_case
            p_norm = p.lower().replace(' ', '_').replace('-', '_')
            if p_norm == 'revengetrading': p_norm = 'revenge_trading'
            if p_norm == 'fomoentries': p_norm = 'fomo_entries'
            if p_norm == 'plannonadherence': p_norm = 'plan_non_adherence'
            if p_norm == 'prematureexit': p_norm = 'premature_exit'
            if p_norm == 'lossrunning': p_norm = 'loss_running'
            if p_norm == 'sessiontilt': p_norm = 'session_tilt'
            if p_norm == 'timeofdaybias': p_norm = 'time_of_day_bias'
            if p_norm == 'positionsizinginconsistency': p_norm = 'position_sizing_inconsistency'
            gt_pathologies.append(p_norm)
            
        sessions = trader.get('sessions', [])
        # trades might be inside sessions or at root, check dataset format
        trades = trader.get('trades', [])
        if not trades:
            for s in sessions:
                trades.extend(s.get('trades', []))
                
        classifier = RuleBasedClassifier(user_id=user_id, sessions=sessions, trades=trades)
        profile = classifier.generate_profile()
        
        pred_pathologies = [p['pathology'] for p in profile['dominantPathologies']]
        
        # We record the primary expected vs predicted for the perTrader report
        primary_gt = gt_pathologies[0] if gt_pathologies else "none"
        primary_pred = pred_pathologies[0] if pred_pathologies else "none"
        correct = primary_gt in pred_pathologies
        
        metrics["perTrader"].append({
            "userId": user_id,
            "name": name,
            "groundTruth": primary_gt,
            "predicted": primary_pred,
            "correct": correct
        })
        
        for p in pathologies:
            is_gt = p in gt_pathologies
            is_pred = p in pred_pathologies
            if is_gt:
                metrics["perClass"][p]["support"] += 1
                
            if is_gt and is_pred:
                metrics["perClass"][p]["tp"] += 1
            elif not is_gt and is_pred:
                metrics["perClass"][p]["fp"] += 1
            elif is_gt and not is_pred:
                metrics["perClass"][p]["fn"] += 1
                
    # Calculate Precision, Recall, F1
    final_report = {
        "perClass": {},
        "macroAvg": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
        "microAvg": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
        "perTrader": metrics["perTrader"]
    }
    
    total_tp = total_fp = total_fn = 0
    
    for p in pathologies:
        tp = metrics["perClass"][p]["tp"]
        fp = metrics["perClass"][p]["fp"]
        fn = metrics["perClass"][p]["fn"]
        support = metrics["perClass"][p]["support"]
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        final_report["perClass"][p] = {
            "precision": round(precision, 2),
            "recall": round(recall, 2),
            "f1": round(f1, 2),
            "support": support
        }
        
        total_tp += tp
        total_fp += fp
        total_fn += fn
        
    # Macro Average
    macro_p = sum(c["precision"] for c in final_report["perClass"].values()) / len(pathologies)
    macro_r = sum(c["recall"] for c in final_report["perClass"].values()) / len(pathologies)
    macro_f1 = sum(c["f1"] for c in final_report["perClass"].values()) / len(pathologies)
    
    final_report["macroAvg"] = {
        "precision": round(macro_p, 2),
        "recall": round(macro_r, 2),
        "f1": round(macro_f1, 2)
    }
    
    # Micro Average
    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = 2 * (micro_p * micro_r) / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0
    
    final_report["microAvg"] = {
        "precision": round(micro_p, 2),
        "recall": round(micro_r, 2),
        "f1": round(micro_f1, 2)
    }
    
    print(json.dumps(final_report, indent=2))
    
    with open('eval_report.json', 'w') as f:
        json.dump(final_report, f, indent=2)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="nevup_seed_dataset.json")
    args = parser.parse_args()
    run_eval(args.data)
