#![feature(proc_macro_hygiene, decl_macro)]
#[macro_use]
extern crate rocket;
use reqwest;
use rocket::State;
use rust_decimal::prelude::*;
use serde::Deserialize;
use serde_json::Value;
use std::collections::BTreeMap;

// define the env vars we're looking for once here as we'll reference
// them in several places later.
const SYMBOL_VAR_KEY: &'static str = "SYMBOL";
const NDAYS_VAR_KEY: &'static str = "NDAYS";
const API_TOKEN_KEY: &'static str = "APIKEY";

// define the upstream API we'll use to pull data from
const STOCK_API: &'static str = "https://www.alphavantage.co";

// primary application configuration object. We'll fill this in with
// data we get from environment variables once and pass it to rocket so
// responses don't have to lookup per request.
struct Config {
    symbol: String,
    ndays: usize,
    api_token: String,
}

fn make_url(api_token: &str, symbol: &str) -> String {
    format!(
        "{}/query?apikey={}&function=TIME_SERIES_DAILY_ADJUSTED&symbol={}",
        STOCK_API, api_token, symbol
    )
}

// https://stackoverflow.com/a/58234247
#[derive(Debug, Deserialize)]
struct StockData {
    #[serde(rename = "4. close")]
    close: String,
}

// use a BTreeeMap to preserve ordering we recieved from upstream API
#[derive(Debug, Deserialize)]
struct APIResponse {
    #[serde(rename = "Time Series (Daily)")]
    result: BTreeMap<String, StockData>,
}

#[get("/")]
fn index(config: State<Config>) -> String {
    let url = make_url(&config.api_token, &config.symbol);
    match reqwest::blocking::get(&url) {
        Ok(res) => {
            let val: Value = serde_json::from_str(&res.text().unwrap()).unwrap();
            let api_response: APIResponse = serde_json::from_value(val).unwrap();
            let mut recent: Vec<&str> = Vec::new();

            // reverse result to order from most recent to oldest dates.
            for (_, v) in api_response.result.iter().rev().take(config.ndays) {
                recent.push(&v.close);
            }

            // use Decimal instead of f64 since we're dealing with financial data
            let average: Decimal = recent
                .iter()
                .map(|x| Decimal::from_str(x).unwrap())
                .sum::<Decimal>()
                / Decimal::from(recent.len());

            format!(
                "{} data=[{}], average={}",
                config.symbol,
                recent.join(", "),
                average
            )
        }
        Err(_) => "err :(".to_string(),
    }
}

fn missing_env_var_exit(env_var_key: &str) {
    eprintln!(
        "environment variable '{}' not found; please set this environment variable to proceed.",
        env_var_key
    );
    std::process::exit(1)
}

// create a Config object which rocket can use to maintain application state
// by reading environment variables
fn make_config(symbol_key: &str, ndays_key: &str, api_token_key: &str) -> Config {
    let mut symbol = String::new();
    let mut ndays: usize = 0;
    let mut api_token = String::new();

    for (k, v) in std::env::vars() {
        if k == symbol_key {
            symbol = v.clone();
        }

        if k == ndays_key {
            ndays = v.clone().parse().unwrap_or(1);
        }

        if k == api_token_key {
            api_token = v.clone();
        }
    }

    // confirm we got the settings we need to proceed
    if symbol.is_empty() {
        missing_env_var_exit(SYMBOL_VAR_KEY);
    }

    if api_token.is_empty() {
        missing_env_var_exit(API_TOKEN_KEY);
    }

    Config {
        symbol,
        ndays,
        api_token,
    }
}

fn main() {
    let config = make_config(SYMBOL_VAR_KEY, NDAYS_VAR_KEY, API_TOKEN_KEY);

    rocket::ignite()
        .manage(config)
        .mount("/", routes![index])
        .launch();
}
