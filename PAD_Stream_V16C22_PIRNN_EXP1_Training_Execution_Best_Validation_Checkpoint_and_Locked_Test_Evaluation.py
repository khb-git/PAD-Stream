from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, os, random, time
import numpy as np

ROOT = Path(__file__).resolve().parent
C18R = ROOT/"output"/"V16_C18R_ALIGNMENT_RESIDUAL_AUDIT"/"V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA = "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"
C19 = ROOT/"output"/"V16_C19_LEAKAGE_SAFE_TRAIN_VALIDATION_TEST_OOD_SPLIT_AUTHORITY_CONTRACT"/"V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA = "399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"
C21S = ROOT/"output"/"V16_C21_PIRNN_TRAINING_OBJECTIVE_HYPERPARAMETER_MODEL_SELECTION_AUTHORITY_CONTRACT"/"PAD_Stream_V16C21_Summary.json"

OUT = ROOT/"output"/"V16_C22_PIRNN_EXP1_TRAINING_EXECUTION_BEST_VALIDATION_CHECKPOINT_LOCKED_TEST_EVALUATION"
OUT.mkdir(parents=True, exist_ok=True)
MODEL = OUT/"V16C22_EXP1_Best_Validation_Model.keras"
HIST = OUT/"V16C22_EXP1_Training_History.csv"
TIMECSV = OUT/"V16C22_EXP1_Test_Metrics_By_Time.csv"
GATES = OUT/"V16C22_Final_Training_Evaluation_Gates.csv"
PRED = OUT/"V16C22_EXP1_Locked_Test_Predictions.npz"
SUMMARY = OUT/"PAD_Stream_V16C22_Summary.json"

SEED=16021
SWC=0.2
SOR=0.2
SWMIN=SWC
SWMAX=1.0-SOR
BATCH=64
MAX_EPOCHS=300
LR=1e-3

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20), b""): h.update(b)
    return h.hexdigest()

def loadj(p):
    if not p.exists(): raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))

def savej(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")

def savecsv(p,rows):
    rows=list(rows)
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16C-22")
    print("PI-RNN EXP1 Training, Best-Validation Checkpoint and Locked-Test Evaluation")
    print("="*78)
    print("""
C21 AUTHORIZED TRAINING UNDER ONE PREDECLARED EXP1 PROTOCOL.

C22 NOW TRAINS EXACTLY THAT MODEL:
  201 x 9 sequence
    -> LSTM(64, return_sequences=True)
    -> LSTM(64, return_sequences=True)
    -> TimeDistributed Dense(1)
    -> bounded Sw in [0.2,0.8].

MODEL SELECTION USES VALIDATION MSE ONLY.
THE LOCKED TEST SET IS EVALUATED ONLY AFTER THE BEST VALIDATION CHECKPOINT
HAS BEEN RESTORED. NO RETUNING OCCURS AFTER TEST METRICS ARE OBSERVED.

C22 ALSO REPORTS STRUCTURAL PHYSICS DIAGNOSTICS ON THE LOCKED TEST SET:
bounds, inlet behavior, spatial front ordering, and temporal ordering.
THE FULL C10/C11 DIFFERENTIAL-OPERATOR RESIDUAL IS NOT USED TO SELECT OR
RETUNE EXP1; it remains an independent post-prediction audit.
""")
    if sha(C18R)!=C18R_SHA: raise RuntimeError("C18R hash mismatch")
    if sha(C19)!=C19_SHA: raise RuntimeError("C19 hash mismatch")
    c21=loadj(C21S)
    if c21.get("status")!="V16C_PIRNN_EXP1_TRAINING_PROTOCOL_FROZEN_TRAINING_AUTHORIZED":
        raise RuntimeError("C21 training authorization missing")

    os.environ["PYTHONHASHSEED"]=str(SEED)
    random.seed(SEED)
    np.random.seed(SEED)

    import tensorflow as tf
    tf.keras.utils.set_random_seed(SEED)
    try:
        tf.config.experimental.enable_op_determinism()
        deterministic=True
    except Exception:
        deterministic=False

    with np.load(C18R,allow_pickle=False) as z:
        xr=np.asarray(z["X_sequence_required"],dtype=np.float32)
        y=np.asarray(z["Y_transport"],dtype=np.float32)
        th=np.asarray(z["target_time_hat"],dtype=np.float32)
        es=np.asarray(z["target_eta_sequence"],dtype=np.float32)
        td=np.asarray(z["target_time_days"],dtype=np.float64)
        si=np.asarray(z["streamline_index"],dtype=np.int64)
        ti=np.asarray(z["time_index"],dtype=np.int64)
    with np.load(C19,allow_pickle=False) as z:
        part=np.asarray(z["sample_partition_code"],dtype=np.int8)

    # Exact C20 deterministic 9-channel construction.
    T=np.broadcast_to(th[:,None,None],(len(th),201,1)).astype(np.float32)
    E=es[:,:,None].astype(np.float32)
    X=np.concatenate([xr,T,E],axis=2).astype(np.float32)

    train=part==0; val=part==1; test=part==2
    if (int(train.sum()),int(val.sum()),int(test.sum()))!=(6795,1458,1449):
        raise RuntimeError("C19 partition counts changed")

    # No normalization fit. Inputs are consumed exactly in frozen representation.
    inp=tf.keras.Input(shape=(201,9),name="v16_required_sequence")
    h=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_1")(inp)
    h=tf.keras.layers.LSTM(64,return_sequences=True,name="lstm_2")(h)
    raw=tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(1),name="td_dense")(h)
    sw=tf.keras.layers.Lambda(
        lambda q: tf.cast(SWC,tf.float32)+tf.cast(1.0-SWC-SOR,tf.float32)*tf.math.sigmoid(q),
        name="bounded_saturation"
    )(raw)
    out=tf.keras.layers.Reshape((201,),name="Sw_sequence")(sw)
    model=tf.keras.Model(inp,out,name="PAD_Stream_V16C22_EXP1")
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=LR),loss="mse",metrics=["mae"])

    callbacks=[
        tf.keras.callbacks.ModelCheckpoint(str(MODEL),monitor="val_loss",mode="min",save_best_only=True,verbose=1),
        tf.keras.callbacks.EarlyStopping(monitor="val_loss",mode="min",patience=30,min_delta=1e-6,restore_best_weights=True,verbose=1),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss",mode="min",factor=0.5,patience=10,min_lr=1e-6,verbose=1),
    ]

    print("TRAINING EXECUTION")
    print(f"  TensorFlow             : {tf.__version__}")
    print(f"  deterministic ops      : {deterministic}")
    print(f"  train/val/test         : {train.sum()} / {val.sum()} / {test.sum()}")
    print(f"  batch / max epochs     : {BATCH} / {MAX_EPOCHS}")
    print(f"  seed                   : {SEED}")
    print(f"  test touched pre-fit   : False")

    t0=time.time()
    history=model.fit(
        X[train],y[train],
        validation_data=(X[val],y[val]),
        epochs=MAX_EPOCHS,batch_size=BATCH,shuffle=True,
        callbacks=callbacks,verbose=2
    )
    elapsed=time.time()-t0

    # Explicitly reload the best validation checkpoint before the one locked-test evaluation.
    best=tf.keras.models.load_model(MODEL,safe_mode=False)
    hist=history.history
    epochs=len(hist["loss"])
    best_epoch=int(np.argmin(hist["val_loss"])+1)
    best_val=float(np.min(hist["val_loss"]))
    rows=[]
    for k in range(epochs):
        rows.append({
            "epoch":k+1,
            "loss":float(hist["loss"][k]),
            "mae":float(hist["mae"][k]),
            "val_loss":float(hist["val_loss"][k]),
            "val_mae":float(hist["val_mae"][k]),
            "learning_rate":float(hist.get("learning_rate",[np.nan]*epochs)[k])
        })
    savecsv(HIST,rows)

    # FIRST and only test evaluation in this script, after model selection.
    test_eval=best.evaluate(X[test],y[test],batch_size=BATCH,verbose=0,return_dict=True)
    yp=best.predict(X[test],batch_size=BATCH,verbose=0).astype(np.float32)
    yt=y[test]
    err=yp-yt
    mse=float(np.mean(err.astype(np.float64)**2))
    rmse=float(np.sqrt(mse))
    mae=float(np.mean(np.abs(err.astype(np.float64))))
    maxae=float(np.max(np.abs(err.astype(np.float64))))
    r2_den=float(np.sum((yt.astype(np.float64)-np.mean(yt.astype(np.float64)))**2))
    r2=1.0-float(np.sum(err.astype(np.float64)**2))/r2_den if r2_den>0 else float("nan")

    # Structural physics diagnostics.
    bound_violation=float(max(0.0,SWMIN-float(np.min(yp)),float(np.max(yp))-SWMAX))
    inlet_mae=float(np.mean(np.abs(yp[:,0]-yt[:,0])))
    spatial_positive_frac=float(np.mean(np.diff(yp.astype(np.float64),axis=1)>1e-7))

    # Temporal ordering within each held-out streamline.
    test_idx=np.where(test)[0]
    neg=0; total=0
    for g in np.unique(si[test]):
        idx=test_idx[si[test]==g]
        idx=idx[np.argsort(td[idx])]
        if len(idx)>1:
            d=np.diff(yp[np.searchsorted(test_idx,idx)] if False else yp[[np.where(test_idx==q)[0][0] for q in idx]],axis=0)
            neg += int(np.sum(d < -1e-6))
            total += d.size
    temporal_negative_frac=float(neg/total) if total else 0.0

    # Per-time locked test metrics.
    timerows=[]
    test_days=td[test]
    for d in np.unique(test_days):
        m=test_days==d
        e=(yp[m].astype(np.float64)-yt[m].astype(np.float64))
        timerows.append(dict(
            target_day=float(d),samples=int(m.sum()),
            mse=float(np.mean(e**2)),rmse=float(np.sqrt(np.mean(e**2))),
            mae=float(np.mean(np.abs(e))),max_abs_error=float(np.max(np.abs(e)))
        ))
    savecsv(TIMECSV,timerows)

    np.savez_compressed(
        PRED,
        Y_true=yt,Y_pred=yp,error=err,
        target_time_days=td[test],time_index=ti[test],streamline_index=si[test],
        sample_indices=test_idx,
        authority_label_ascii=np.frombuffer(b"V16C22_EXP1_LOCKED_TEST_EVALUATION_NO_RETUNING",dtype=np.uint8)
    )

    model_sha=sha(MODEL); pred_sha=sha(PRED)
    finite=bool(np.all(np.isfinite(yp)))
    gates=[
        ("C21_training_authorization_reproduced",True),
        ("C18R_exact_hash_reproduced",sha(C18R)==C18R_SHA),
        ("C19_exact_hash_reproduced",sha(C19)==C19_SHA),
        ("train_count_6795",int(train.sum())==6795),
        ("validation_count_1458",int(val.sum())==1458),
        ("test_count_1449",int(test.sum())==1449),
        ("architecture_201_nodes_9_channels",X.shape[1:]==(201,9)),
        ("two_LSTM64_layers_used",sum(isinstance(l,tf.keras.layers.LSTM) and l.units==64 for l in best.layers)==2),
        ("bounded_output_mapping_used",True),
        ("Adam_initial_lr_1e_3",LR==1e-3),
        ("batch_size_64",BATCH==64),
        ("max_epochs_300",MAX_EPOCHS==300),
        ("validation_only_checkpoint_selection",True),
        ("best_validation_checkpoint_saved",MODEL.exists()),
        ("best_validation_checkpoint_reloaded_before_test",True),
        ("locked_test_not_used_for_training_or_selection",True),
        ("locked_test_evaluated_after_model_selection",True),
        ("predictions_finite",finite),
        ("predictions_within_bounded_output",bound_violation<=1e-7),
        ("no_normalization_refit",True),
        ("no_optional_feature_promotion",True),
        ("no_hyperparameter_retuning_after_test",True),
        ("OOD_not_claimed",True),
        ("full_operator_residual_not_used_for_model_selection",True),
    ]
    savecsv(GATES,[dict(gate=g,passed=bool(v)) for g,v in gates])
    ok=all(v for _,v in gates)

    if ok:
        status="V16C_PIRNN_EXP1_TRAINED_BEST_VALIDATION_CHECKPOINT_LOCKED_TEST_EVALUATED"
        diagnosis="EXP1_WAS_TRAINED_UNDER_THE_FROZEN_C21_PROTOCOL_AND_THE_BEST_VALIDATION_CHECKPOINT_WAS_EVALUATED_ON_THE_PREVIOUSLY_LOCKED_TEST_SET_WITHOUT_RETUNING"
        rec=("Freeze the C22 checkpoint, history, and locked-test predictions. Next perform an independent C10/C11 Pollock full-physics residual audit and detailed error/front diagnostics on the frozen predictions before deciding whether EXP1 is accepted as the V16 baseline.")
        nxt="V16C-23 — Frozen EXP1 Prediction Full-Physics Residual and Error-Structure Certification Audit"
    else:
        status="V16C_PIRNN_EXP1_EXECUTION_CERTIFICATION_BLOCKED"
        diagnosis="ONE_OR_MORE_TRAINING_EXECUTION_CHECKPOINT_TEST_LOCK_OR_NUMERICAL_GATES_FAILED"
        rec="Do not retune. Audit only the failed C22 execution gate under the frozen C21 protocol."
        nxt="V16C-22R — EXP1 Training Execution Residual Audit"

    savej(SUMMARY,dict(
        milestone="V16C-22",status=status,diagnosis=diagnosis,
        tensorflow_version=tf.__version__,deterministic_ops=deterministic,seed=SEED,
        epochs_completed=epochs,best_epoch=best_epoch,best_validation_mse=best_val,
        elapsed_seconds=elapsed,
        locked_test=dict(mse=mse,rmse=rmse,mae=mae,max_abs_error=maxae,r2=r2,
                         keras_loss=float(test_eval["loss"]),keras_mae=float(test_eval["mae"])),
        structural_physics=dict(bound_violation=bound_violation,inlet_mae=inlet_mae,
            spatial_positive_fraction=spatial_positive_frac,temporal_negative_fraction=temporal_negative_frac),
        model_sha256=model_sha,prediction_artifact_sha256=pred_sha,
        test_used_for_selection=False,retuning_after_test=False,
        recommendation=rec,next_milestone=nxt
    ))

    print("\nTRAINING / LOCKED-TEST RESULT")
    print(f"  epochs completed        : {epochs}")
    print(f"  best epoch              : {best_epoch}")
    print(f"  best validation MSE     : {best_val:.8e}")
    print(f"  elapsed seconds         : {elapsed:.2f}")
    print(f"  locked test MSE         : {mse:.8e}")
    print(f"  locked test RMSE        : {rmse:.8e}")
    print(f"  locked test MAE         : {mae:.8e}")
    print(f"  locked test max |error| : {maxae:.8e}")
    print(f"  locked test R2          : {r2:.8f}")
    print(f"  bound violation         : {bound_violation:.3e}")
    print(f"  inlet MAE               : {inlet_mae:.3e}")
    print(f"  spatial positive frac   : {spatial_positive_frac:.3e}")
    print(f"  temporal negative frac  : {temporal_negative_frac:.3e}")

    print("\n"+"="*78)
    print("V16C-22 FINAL TRAINING / EVALUATION GATES")
    print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",rec)
    print("\nNEXT MILESTONE\n ",nxt)
    print("\nArtifacts")
    print("  Model:",MODEL,"\n    SHA-256:",model_sha)
    print("  Test predictions:",PRED,"\n    SHA-256:",pred_sha)
    print("\n"+"="*78)
    print("PAD-STREAM V16C-22 EXP1 TRAINING / LOCKED TEST: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
