import datacollect
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score

from yfCollectData import stockDataCollection

plt.style.use('ggplot')

def trainModel(ticker_symbol):
    training_data = stockDataCollection(ticker_symbol) # gets training data from the yfCollectData subroutine

    X = training_data[['Volume', '52 Week Range Position', 'Top Sector ETF Close', 'Daily Returns']] # Sets features
    y = training_data[['Close']] # Sets what we're predicting to be the close value of the stock

    print(f"✅ Dataset shape: {training_data.shape}")
    print(f"Features used in model: {X.columns.tolist()}")

    # setting test/train split to be 20%
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # setting the parameters of the training
    degree = 2 # highest power of the polynomial
    use_ridge = True # sets it to be a polynomial instead of linear regression
    ridge_alpha = 1.0

    # setting the weights of each feature, can be adjusted later
    weight_Volume = 0.172
    weight_52_week_pos = 0.264
    weight_etf = 0.466
    weight_daily_returns = 0.097

    # apply weights
    X_train_w = X_train.copy()
    X_test_w = X_test.copy()

    X_train_w['Volume'] = X_train_w['Volume'] * weight_Volume
    X_train_w['52 Week Range Position'] = X_train_w['52 Week Range Position'] * weight_52_week_pos
    X_train_w['Top Sector ETF Close'] = X_train_w['Top Sector ETF Close'] * weight_etf
    X_train_w['Daily Returns'] = X_train_w['Daily Returns'] * weight_daily_returns

    X_test_w['Volume'] = X_test_w['Volume'] * weight_Volume
    X_test_w['52 Week Range Position'] = X_test_w['52 Week Range Position'] * weight_52_week_pos
    X_test_w['Top Sector ETF Close'] = X_test_w['Top Sector ETF Close'] * weight_etf
    X_test_w['Daily Returns'] = X_test_w['Daily Returns'] * weight_daily_returns

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train_w)
    X_test_scaled = scaler.transform(X_test_w)

    poly = PolynomialFeatures(degree=degree, include_bias=False)

    X_train_poly = poly.fit_transform(X_train_scaled)
    X_test_poly = poly.transform(X_test_scaled)

    print(f"Polynomial features shape: {X_train_poly.shape}")

    # seeing if the user wants a polynomial or linear regression model
    if use_ridge:
        model = Ridge(alpha=ridge_alpha)
        print(f"   Using Ridge (alpha={ridge_alpha})")
    else:
        model = LinearRegression()
        print("   Using Linear Regression")

    # training the model
    model.fit(X_train_poly, y_train)
    print("✅ Model training complete.")

    # feature importance
    feature_names = poly.get_feature_names_out(X.columns)
    coef_values = np.abs(model.coef_).ravel()

    coef_df = pd.DataFrame({
        'Feature': feature_names,
        'Abs Coefficient': coef_values
    })

    volume_terms = [f for f in feature_names if 'Volume' in f]
    week_52_pos_terms = [f for f in feature_names if '52 Week Range Position' in f]
    etf_terms = [f for f in feature_names if 'Top Sector ETF Close' in f]
    daily_returns_terms = [f for f in feature_names if 'Daily Returns' in f]

    volume_imp = coef_df[coef_df['Feature'].isin(volume_terms)]['Abs Coefficient'].sum()
    week_52_pos_imp = coef_df[coef_df['Feature'].isin(week_52_pos_terms)]['Abs Coefficient'].sum()
    etf_imp = coef_df[coef_df['Feature'].isin(etf_terms)]['Abs Coefficient'].sum()
    daily_returns_imp = coef_df[coef_df['Feature'].isin(daily_returns_terms)]['Abs Coefficient'].sum()

    total = volume_imp + week_52_pos_imp + etf_imp + daily_returns_imp
    print("\n📊 Relative Feature Importance (%):")
    print(f"   Volume          : {(volume_imp / total * 100):.1f}%")
    print(f"   52 Week Position    : {(week_52_pos_imp / total * 100):.1f}%")
    print(f"   Top Sector ETF Close    : {(etf_imp / total * 100):.1f}%")
    print(f"   Daily Returns    : {(daily_returns_imp / total * 100):.1f}%")
    print(f"   (Total: 100.0%)")

    y_test_pred = model.predict(X_test_poly)
    print(f"\nTest R²:    {r2_score(y_test, y_test_pred):.4f}")
    print(f"Test MAE:   {mean_absolute_error(y_test, y_test_pred):.4f}")

    os.makedirs("poly", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("scaler", exist_ok=True)

    poly_path = os.path.join("poly", f"{ticker_symbol}_poly_transformer_grades.pkl")
    model_path = os.path.join("models", f"{ticker_symbol}_polynomial_regression_model_grades.pkl")
    scaler_path = os.path.join("scaler", f"{ticker_symbol}_scaler_grades.pkl")

    joblib.dump(poly, poly_path)
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"✅ Saved polynomial transformer to {poly_path}")
    print(f"✅ Saved model to {model_path}")
    print(f"✅ Saved scaler to {scaler_path}")

    # Plot actual vs predicted stock close price
    y_test_flat = y_test.values.ravel()
    y_test_pred_flat = y_test_pred.ravel()

    min_price = min(y_test_flat.min(), y_test_pred_flat.min())
    max_price = max(y_test_flat.max(), y_test_pred_flat.max())

    plt.figure(figsize=(10, 6))
    plt.scatter(
        y_test_flat,
        y_test_pred_flat,
        color='steelblue',
        alpha=0.7,
        s=50
    )
    plt.plot([min_price, max_price], [min_price, max_price], 'r--', lw=2)
    plt.xlabel("Actual Close Price")
    plt.ylabel("Predicted Close Price")
    plt.title(f"{ticker_symbol}: Actual vs Predicted Close Price (degree={degree})")
    plt.grid(True)
    plt.show()